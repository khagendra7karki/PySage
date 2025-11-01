#include "utils.hpp"
#include "ContextExtractor.hpp"
#include "DataTypes.hpp"

// for web ui
#include "index.html.gz.hpp"
#include "loading.html.hpp"

std::function<void(int)> shutdown_handler;
std::atomic_flag is_terminating = ATOMIC_FLAG_INIT;

inline void signal_handler(int signal) {
    if (is_terminating.test_and_set()) {
        fprintf(stderr, "Received second interrupt, terminating immediately.\n");
        exit(1);
    }

    shutdown_handler(signal);
}

int main(int argc, char ** argv) {
    common_params params;

    if (!common_params_parse(argc, argv, params, LLAMA_EXAMPLE_SERVER)) {
        return 1;
    }

    common_init();

    server_context ctx_server;

    llama_backend_init();
    llama_numa_init(params.numa);

    LOG_INF("system info: n_threads = %d, n_threads_batch = %d, total_threads = %d\n", params.cpuparams.n_threads, params.cpuparams_batch.n_threads, std::thread::hardware_concurrency());
    LOG_INF("\n");
    LOG_INF("%s\n", common_params_get_system_info(params).c_str());
    LOG_INF("\n");

    std::unique_ptr<httplib::Server> svr;

    if (params.ssl_file_key != "" && params.ssl_file_cert != "") {
        LOG_ERR("Server is built without SSL support\n");
        return 1;
    }
    svr.reset(new httplib::Server());


    std::atomic<server_state> state{SERVER_STATE_LOADING_MODEL};

    svr->set_default_headers({{"Server", "llama.cpp"}});
    svr->set_logger(log_server_request);

    auto res_error = [](httplib::Response & res, const json & error_data) {
        json final_response {{"error", error_data}};
        res.set_content(safe_json_to_str(final_response), MIMETYPE_JSON);
        res.status = json_value(error_data, "code", 500);
    };

    auto res_ok = [](httplib::Response & res, const json & data) {
        res.set_content(safe_json_to_str(data), MIMETYPE_JSON);
        res.status = 200;
    };

    svr->set_exception_handler([&res_error](const httplib::Request &, httplib::Response & res, const std::exception_ptr & ep) {
        std::string message;
        try {
            std::rethrow_exception(ep);
        } catch (const std::exception & e) {
            message = e.what();
        } catch (...) {
            message = "Unknown Exception";
        }

        try {
            json formatted_error = format_error_response(message, ERROR_TYPE_SERVER);
            LOG_WRN("got exception: %s\n", formatted_error.dump().c_str());
            res_error(res, formatted_error);
        } catch (const std::exception & e) {
            LOG_ERR("got another exception: %s | while hanlding exception: %s\n", e.what(), message.c_str());
        }
    });

    svr->set_error_handler([&res_error](const httplib::Request &, httplib::Response & res) {
        if (res.status == 404) {
            res_error(res, format_error_response("File Not Found", ERROR_TYPE_NOT_FOUND));
        }
    });

    svr->set_read_timeout (params.timeout_read);
    svr->set_write_timeout(params.timeout_write);

    std::unordered_map<std::string, std::string> log_data;
    log_data["hostname"] = params.hostname;
    log_data["port"]     = std::to_string(params.port);



    ctx_server.slot_prompt_similarity = params.slot_prompt_similarity;


    auto middleware_server_state = [&res_error, &state](const httplib::Request & req, httplib::Response & res) {
        server_state current_state = state.load();
        if (current_state == SERVER_STATE_LOADING_MODEL) {
            auto tmp = string_split<std::string>(req.path, '.');
            if (req.path == "/" || tmp.back() == "html") {
                res.set_content(reinterpret_cast<const char*>(loading_html), loading_html_len, "text/html; charset=utf-8");
                res.status = 503;
            } else {
                res_error(res, format_error_response("Loading model", ERROR_TYPE_UNAVAILABLE));
            }
            return false;
        }
        return true;
    };

    svr->set_pre_routing_handler([ &middleware_server_state](const httplib::Request & req, httplib::Response & res) {
        res.set_header("Access-Control-Allow-Origin", req.get_header_value("Origin"));
        if (req.method == "OPTIONS") {
            res.set_header("Access-Control-Allow-Credentials", "true");
            res.set_header("Access-Control-Allow-Methods",     "GET, POST");
            res.set_header("Access-Control-Allow-Headers",     "*");
            res.set_content("", "text/html");
            return httplib::Server::HandlerResponse::Handled;
        }
        if (!middleware_server_state(req, res)) {
            return httplib::Server::HandlerResponse::Handled;
        }
        return httplib::Server::HandlerResponse::Unhandled;
    });

    const auto handle_infill = [&ctx_server, &res_error, &res_ok](const httplib::Request & req, httplib::Response & res) {
        std::string err;
        if (llama_vocab_fim_pre(ctx_server.vocab) == LLAMA_TOKEN_NULL) {
            err += "prefix token is missing. ";
        }
        if (llama_vocab_fim_suf(ctx_server.vocab) == LLAMA_TOKEN_NULL) {
            err += "suffix token is missing. ";
        }
        if (llama_vocab_fim_mid(ctx_server.vocab) == LLAMA_TOKEN_NULL) {
            err += "middle token is missing. ";
        }
        if (!err.empty()) {
            res_error(res, format_error_response(string_format("Infill is not supported by this model: %s", err.c_str()), ERROR_TYPE_NOT_SUPPORTED));
            return;
        }

        json data = json::parse(req.body);

        if (data.contains("prompt") && !data.at("prompt").is_string()) {
            res_error(res, format_error_response("\"prompt\" must be a string", ERROR_TYPE_INVALID_REQUEST));
        }

        if (!data.contains("input_prefix")) {
            res_error(res, format_error_response("\"input_prefix\" is required", ERROR_TYPE_INVALID_REQUEST));
        }

        if (!data.contains("input_suffix")) {
            res_error(res, format_error_response("\"input_suffix\" is required", ERROR_TYPE_INVALID_REQUEST));
        }

        if (data.contains("input_extra") && !data.at("input_extra").is_array()) {
            res_error(res, format_error_response("\"input_extra\" must be an array of {\"filename\": string, \"text\": string}", ERROR_TYPE_INVALID_REQUEST));
            return;
        }

        json input_extra = json_value(data, "input_extra", json::array());
        for (const auto & chunk : input_extra) {
            if (!chunk.contains("text") || !chunk.at("text").is_string()) {
                res_error(res, format_error_response("extra_context chunk must contain a \"text\" field with a string value", ERROR_TYPE_INVALID_REQUEST));
                return;
            }
            if (chunk.contains("filename") && !chunk.at("filename").is_string()) {
                res_error(res, format_error_response("extra_context chunk's \"filename\" field must be a string", ERROR_TYPE_INVALID_REQUEST));
                return;
            }
        }
        data["input_extra"] = input_extra;

        std::string prompt = json_value(data, "prompt", std::string());
        std::vector<llama_tokens> tokenized_prompts = tokenize_input_prompts(ctx_server.vocab, prompt, false, true);
        SRV_DBG("creating infill tasks, n_prompts = %d\n", (int) tokenized_prompts.size());
        data["prompt"] = format_infill(
            ctx_server.vocab,
            data.at("input_prefix"),
            data.at("input_suffix"),
            data.at("input_extra"),
            ctx_server.params_base.n_batch,
            ctx_server.params_base.n_predict,
            ctx_server.slots[0].n_ctx,
            ctx_server.params_base.spm_infill,
            tokenized_prompts[0]
        );

        server_task_type type = SERVER_TASK_TYPE_INFILL;
        auto completion_id = gen_chatcmplid();
        std::vector<server_task> tasks;

        try {
            const auto & prompt = data.at("prompt");
            std::vector<llama_tokens> tokenized_prompts = tokenize_input_prompts(ctx_server.vocab, prompt, true, true);
            tasks.reserve(tokenized_prompts.size());
            for (size_t i = 0; i < tokenized_prompts.size(); i++) {
                server_task task = server_task(type);

                task.id    = ctx_server.queue_tasks.get_new_id();
                task.index = i;

                task.prompt_tokens    = std::move(tokenized_prompts[i]);
                task.params           = server_task::params_from_json_cmpl(
                                            ctx_server.ctx,
                                            ctx_server.params_base,
                                            data);
                task.id_selected_slot = json_value(data, "id_slot", -1);

                tasks.push_back(task);
            }
        } catch (const std::exception & e) {
            res_error(res, format_error_response(e.what(), ERROR_TYPE_INVALID_REQUEST));
            return;
        }

        ctx_server.queue_results.add_waiting_tasks(tasks);
        ctx_server.queue_tasks.post(tasks);

        bool stream = json_value(data, "stream", false);
        const auto task_ids = server_task::get_list_id(tasks);

        if (!stream) {
            ctx_server.receive_multi_results(task_ids, [&](std::vector<server_task_result_ptr> & results) {
                if (results.size() == 1) {
                    res_ok(res, results[0]->to_json());
                } else {
                    json arr = json::array();
                    for (auto & res : results) {
                        arr.push_back(res->to_json());
                    }
                    res_ok(res, arr);
                }
            }, [&](const json & error_data) {
                res_error(res, error_data);
            }, req.is_connection_closed);

            ctx_server.queue_results.remove_waiting_task_ids(task_ids);
        } else {
            const auto chunked_content_provider = [task_ids, &ctx_server](size_t, httplib::DataSink & sink) {
                ctx_server.receive_cmpl_results_stream(task_ids, [&](server_task_result_ptr & result) -> bool {
                    json res_json = result->to_json();
                    if (res_json.is_array()) {
                        for (const auto & res : res_json) {
                            if (!server_sent_event(sink, "data", res)) {
                                return false;
                            }
                        }
                        return true;
                    } else {
                        return server_sent_event(sink, "data", res_json);
                    }
                }, [&](const json & error_data) {
                    server_sent_event(sink, "error", error_data);
                }, [&sink]() {
                    return !sink.is_writable();
                });
                sink.done();
                return false;
            };

            auto on_complete = [task_ids, &ctx_server] (bool) {
                ctx_server.queue_results.remove_waiting_task_ids(task_ids);
            };

            res.set_chunked_content_provider("text/event-stream", chunked_content_provider, on_complete);
        }
    };

    const auto handle_chat_completions = [&ctx_server, &params, &res_error, &res_ok](const httplib::Request & req, httplib::Response & res) {
        LOG_DBG("request: %s\n", req.body.c_str());
        if (ctx_server.params_base.embedding) {
            res_error(res, format_error_response("This server does not support completions. Start it without `--embeddings`", ERROR_TYPE_NOT_SUPPORTED));
            return;
        }

        auto body = json::parse(req.body);
        json data = oaicompat_completion_params_parse(body, params.use_jinja, params.reasoning_format, ctx_server.chat_templates.get());

        server_task_type type = SERVER_TASK_TYPE_COMPLETION;
        auto completion_id = gen_chatcmplid();
        std::vector<server_task> tasks;

        try {
            const auto & prompt = data.at("prompt");
            std::vector<llama_tokens> tokenized_prompts = tokenize_input_prompts(ctx_server.vocab, prompt, true, true);
            tasks.reserve(tokenized_prompts.size());
            for (size_t i = 0; i < tokenized_prompts.size(); i++) {
                server_task task = server_task(type);

                task.id    = ctx_server.queue_tasks.get_new_id();
                task.index = i;

                task.prompt_tokens    = std::move(tokenized_prompts[i]);
                task.params           = server_task::params_from_json_cmpl(
                                            ctx_server.ctx,
                                            ctx_server.params_base,
                                            data);
                task.id_selected_slot = json_value(data, "id_slot", -1);

                task.params.oaicompat                 = OAICOMPAT_TYPE_CHAT;
                task.params.oaicompat_cmpl_id         = completion_id;

                tasks.push_back(task);
            }
        } catch (const std::exception & e) {
            res_error(res, format_error_response(e.what(), ERROR_TYPE_INVALID_REQUEST));
            return;
        }

        ctx_server.queue_results.add_waiting_tasks(tasks);
        ctx_server.queue_tasks.post(tasks);

        bool stream = json_value(data, "stream", false);
        const auto task_ids = server_task::get_list_id(tasks);

        if (!stream) {
            ctx_server.receive_multi_results(task_ids, [&](std::vector<server_task_result_ptr> & results) {
                if (results.size() == 1) {
                    res_ok(res, results[0]->to_json());
                } else {
                    json arr = json::array();
                    for (auto & res : results) {
                        arr.push_back(res->to_json());
                    }
                    res_ok(res, arr);
                }
            }, [&](const json & error_data) {
                res_error(res, error_data);
            }, req.is_connection_closed);

            ctx_server.queue_results.remove_waiting_task_ids(task_ids);
        } else {
            const auto chunked_content_provider = [task_ids, &ctx_server](size_t, httplib::DataSink & sink) {
                ctx_server.receive_cmpl_results_stream(task_ids, [&](server_task_result_ptr & result) -> bool {
                    json res_json = result->to_json();
                    if (res_json.is_array()) {
                        for (const auto & res : res_json) {
                            if (!server_sent_event(sink, "data", res)) {
                                return false;
                            }
                        }
                        return true;
                    } else {
                        return server_sent_event(sink, "data", res_json);
                    }
                }, [&](const json & error_data) {
                    server_sent_event(sink, "error", error_data);
                }, [&sink]() {
                    return !sink.is_writable();
                });
                static const std::string ev_done = "data: [DONE]\n\n";
                sink.write(ev_done.data(), ev_done.size());
                sink.done();
                return false;
            };

            auto on_complete = [task_ids, &ctx_server] (bool) {
                ctx_server.queue_results.remove_waiting_task_ids(task_ids);
            };

            res.set_chunked_content_provider("text/event-stream", chunked_content_provider, on_complete);
        }
    };

    if (!params.webui) {
        LOG_INF("Web UI is disabled\n");
    } else {
        if (!params.public_path.empty()) {
            bool is_found = svr->set_mount_point("/", params.public_path);
            if (!is_found) {
                LOG_ERR("%s: static assets path not found: %s\n", __func__, params.public_path.c_str());
                return 1;
            }
        } else {
            svr->Get("/", [](const httplib::Request & req, httplib::Response & res) {
                if (req.get_header_value("Accept-Encoding").find("gzip") == std::string::npos) {
                    res.set_content("Error: gzip is not supported by this browser", "text/plain");
                } else {
                    res.set_header("Content-Encoding", "gzip");
                    res.set_header("Cross-Origin-Embedder-Policy", "require-corp");
                    res.set_header("Cross-Origin-Opener-Policy", "same-origin");
                    res.set_content(reinterpret_cast<const char*>(index_html_gz), index_html_gz_len, "text/html; charset=utf-8");
                }
                return false;
            });
        }
    }

    // routers

    svr->Post("/infill", handle_infill);
    svr->Post("/v1/chat/completions", handle_chat_completions);

    if (params.n_threads_http < 1) {
        params.n_threads_http = std::max(params.n_parallel + 2, (int32_t) std::thread::hardware_concurrency() - 1);
    }
    log_data["n_threads_http"] =  std::to_string(params.n_threads_http);
    svr->new_task_queue = [&params] { return new httplib::ThreadPool(params.n_threads_http); };

    auto clean_up = [&svr, &ctx_server]() {
        SRV_INF("%s: cleaning up before exit...\n", __func__);
        svr->stop();
        ctx_server.queue_results.terminate();
        llama_backend_free();
    };

    bool was_bound = false;
    if (string_ends_with(std::string(params.hostname), ".sock")) {
        LOG_INF("%s: setting address family to AF_UNIX\n", __func__);
        svr->set_address_family(AF_UNIX);
        was_bound = svr->bind_to_port(params.hostname, 8080);
    } else {
        LOG_INF("%s: binding port with default address family\n", __func__);
        if (params.port == 0) {
            int bound_port = svr->bind_to_any_port(params.hostname);
            if ((was_bound = (bound_port >= 0))) {
                params.port = bound_port;
            }
        } else {
            was_bound = svr->bind_to_port(params.hostname, params.port);
        }
    }

    if (!was_bound) {
        LOG_ERR("%s: couldn't bind HTTP server socket, hostname: %s, port: %d\n", __func__, params.hostname.c_str(), params.port);
        clean_up();
        return 1;
    }

    std::thread t([&]() { svr->listen_after_bind(); });
    svr->wait_until_ready();

    LOG_INF("%s: HTTP server is listening, hostname: %s, port: %d, http threads: %d\n", __func__, params.hostname.c_str(), params.port, params.n_threads_http);

    LOG_INF("%s: loading model\n", __func__);

    if (!ctx_server.load_model(params)) {
        clean_up();
        t.join();
        LOG_ERR("%s: exiting due to model loading error\n", __func__);
        return 1;
    }

    ctx_server.init();
    state.store(SERVER_STATE_READY);

    LOG_INF("%s: model loaded\n", __func__);

    LOG_INF("%s: chat template, chat_template: %s, example_format: '%s'\n", __func__,
        common_chat_templates_source(ctx_server.chat_templates.get()),
        common_chat_format_example(ctx_server.chat_templates.get(), ctx_server.params_base.use_jinja).c_str());

    ctx_server.queue_tasks.on_new_task([&ctx_server](const server_task & task) {
        ctx_server.process_single_task(task);
    });

    ctx_server.queue_tasks.on_update_slots([&ctx_server]() {
        ctx_server.update_slots();
    });

    shutdown_handler = [&](int) {
        ctx_server.queue_tasks.terminate();
    };

    struct sigaction sigint_action;
    sigint_action.sa_handler = signal_handler;
    sigemptyset (&sigint_action.sa_mask);
    sigint_action.sa_flags = 0;
    sigaction(SIGINT, &sigint_action, NULL);
    sigaction(SIGTERM, &sigint_action, NULL);


    LOG_INF("%s: server is listening on http://%s:%d - starting the main loop\n", __func__, params.hostname.c_str(), params.port);

    ctx_server.queue_tasks.start_loop();

    clean_up();
    t.join();

    return 0;
}