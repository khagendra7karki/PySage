#pragma once

#include <tree_sitter/api.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <set>
#include <stdexcept>
#include <map>
#include <cstring>
#include "json.hpp"
#include <filesystem>
#include <queue>

extern "C" TSLanguage *tree_sitter_python();


using unordered_json = nlohmann::json;

struct ImportedItem {
    std::string name;          // The name used in the importing file (could be alias)
    std::string original_name; // The original name from the source file
    std::string source_file;   // The file it was imported from

    unordered_json to_json() const {
        return unordered_json{
            {"name", name},
            {"original_name", original_name},
            {"source_file", source_file}
        };
    }
};

struct ImportedDefinition {
    std::string definition;
    std::string path;  // Relative path
    
    unordered_json to_json() const {
        return unordered_json{
            {"definition", definition},
            {"path", path}
        };
    }
};


struct ImportAndAlias {
    std::string import;
    std::string alias;

    unordered_json to_json() const {
        return unordered_json({{"import", import}, {"alias", alias}});
    }
};

struct ImportDesc {
    std::string source;
    std::string type;
    std::vector<ImportAndAlias> imports;

    unordered_json to_json() const {
        unordered_json o = {
            {"source", source},
            {"type", type},
        };

        o["imports"] = unordered_json::array();
        for (const auto& x : imports) {
            o["imports"].push_back(x.to_json());
        }
        return o;
    }
};

struct FileDefinition {
    std::string type;  // "class", "function", or "global"
    std::string name;
    std::string definition;  
    size_t line_number;

    unordered_json to_json() const {
        return unordered_json{
            {"type", type},
            {"name", name},
            {"definition", definition},
            {"line_number", line_number}
        };
    }
};

class ProjectContext {
private:
    std::filesystem::path project_root;
    std::map<std::string, std::vector<ImportDesc>> file_imports;
    std::map<std::string, std::vector<FileDefinition>> file_definitions;
    std::map<std::string, std::set<std::string>> dependency_graph;
    std::map<std::string, std::vector<ImportedItem>> imported_items; // New: tracks imported items per file
    
    TSParser* parser;
    bool verbose;
    std::string current_source;
    TSTree* current_tree;
    TSNode current_root;

    static std::string read_file(const std::string& filename) {
        std::ifstream file(filename);
        if (!file.is_open()) {
            throw std::runtime_error("Failed to open file: " + filename);
        }
        std::stringstream buffer;
        buffer << file.rdbuf();
        return buffer.str();
    }

    std::string get_node_text(TSNode node) const {
        uint32_t start = ts_node_start_byte(node);
        uint32_t end = ts_node_end_byte(node);
        return current_source.substr(start, end - start);
    }

    size_t get_node_line_number(TSNode node) const {
        return ts_node_start_point(node).row + 1;
    }

    std::string import_to_path(const std::string& import_path, bool is_relative = false) const {
        if (import_path.empty()) return "";

        std::filesystem::path path;
        if (is_relative) {
            path = project_root / std::filesystem::path(import_path);
        } else {
            path = project_root / std::filesystem::path(import_path);
        }

        // Try with .py extension first
        auto py_path = path;
        py_path.replace_extension(".py");
        if (std::filesystem::exists(py_path)) {
            return py_path.string();
        }

        // Try as a package (directory with __init__.py)
        auto init_path = path / "__init__.py";
        if (std::filesystem::exists(init_path)) {
            return init_path.string();
        }

        return "";
    }
    // Helper to find definition by name in a file
    std::string find_definition(const std::string& file_path, const std::string& name) const {
        if (!file_definitions.count(file_path)) return "";
        
        for (const auto& def : file_definitions.at(file_path)) {
            if (def.name == name) {
                return def.definition;
            }
        }
        return "";
    }
    // Helper to convert absolute path to relative path
    std::string to_relative_path(const std::string& absolute_path) const {
        std::filesystem::path abs_path(absolute_path);
        std::filesystem::path rel_path = std::filesystem::relative(abs_path, project_root);
        return rel_path.string();
    }
    std::string extract_signature(TSNode node) const {
        if (strcmp(ts_node_type(node), "function_definition") == 0) {
            TSNode name_node = ts_node_child_by_field_name(node, "name", 4);
            TSNode parameters_node = ts_node_child_by_field_name(node, "parameters", 10);
            return get_node_text(name_node) + get_node_text(parameters_node);
        } else if (strcmp(ts_node_type(node), "class_definition") == 0) {
            TSNode name_node = ts_node_child_by_field_name(node, "name", 4);
            return "class " + get_node_text(name_node);
        }
        return "";
    }

    void parse_source(const std::string& source_code) {
        current_source = source_code;
        current_tree = ts_parser_parse_string(parser, nullptr, source_code.c_str(), source_code.length());
        
        if (!current_tree) {
            throw std::runtime_error("Failed to parse tree");
        }
        current_root = ts_tree_root_node(current_tree);
    }

    std::vector<ImportDesc> extract_imports() {
        std::vector<ImportDesc> imports;
        const std::string query_str = R"(
            (import_statement
                ((dotted_name) @import_source)?
                (aliased_import
                    (dotted_name) @import
                    alias: (identifier) @alias)?)
            (import_from_statement
                module_name: [(dotted_name) (relative_import)] @import_source
                ((dotted_name) @import)?
                (aliased_import
                    (dotted_name) @import
                    (identifier) @alias)?)
        )";

        uint32_t error_offset;
        TSQueryError error_type;
        TSQuery* query = ts_query_new(
            tree_sitter_python(),
            query_str.c_str(),
            query_str.size(),
            &error_offset,
            &error_type
        );

        if (!query) {
            throw std::runtime_error("Failed to create query");
        }

        TSQueryCursor* cursor = ts_query_cursor_new();
        ts_query_cursor_exec(cursor, query, current_root);

        TSQueryMatch match;
        while (ts_query_cursor_next_match(cursor, &match)) {
            ImportDesc desc;
            desc.type = (match.pattern_index == 0) ? "import_statement" : "import_from_statement";
            ImportAndAlias current_import;

            for (uint32_t i = 0; i < match.capture_count; i++) {
                TSNode node = match.captures[i].node;
                if (ts_node_is_null(node)) continue;

                std::string node_text = get_node_text(node);
                uint32_t capture_id = match.captures[i].index;

                if (capture_id == 0) {  // import_source
                    desc.source = node_text;
                } else if (capture_id == 1) {  // import
                    if (!current_import.import.empty()) {
                        desc.imports.push_back(current_import);
                        current_import = ImportAndAlias();
                    }
                    current_import.import = node_text;
                } else if (capture_id == 2) {  // alias
                    current_import.alias = node_text;
                    desc.imports.push_back(current_import);
                    current_import = ImportAndAlias();
                }
            }

            if (!current_import.import.empty()) {
                desc.imports.push_back(current_import);
            }

            if (!desc.source.empty() || !desc.imports.empty()) {
                imports.push_back(desc);
            }
        }

        ts_query_cursor_delete(cursor);
        ts_query_delete(query);

        return imports;
    }

    std::vector<FileDefinition> extract_file_definitions() {
        std::vector<FileDefinition> definitions;
        const std::string query_str = R"(
            (module
            (class_definition name: (identifier)@name ) @class)

            (module
            (function_definition name:(identifier)@name) @function)
            ( module
                (expression_statement
                (assignment left:(identifier)@name) @global))
        )";

        uint32_t error_offset;
        TSQueryError error_type;
        TSQuery* query = ts_query_new(
            tree_sitter_python(),
            query_str.c_str(),
            query_str.size(),
            &error_offset,
            &error_type
        );

        if (!query) {
            throw std::runtime_error("Failed to create query");
        }

        TSQueryCursor* cursor = ts_query_cursor_new();
        ts_query_cursor_exec(cursor, query, current_root);

        TSQueryMatch match;
        while (ts_query_cursor_next_match(cursor, &match)) {
            FileDefinition def;
            def.line_number = 0;

            for (uint32_t i = 0; i < match.capture_count; i++) {
                TSNode node = match.captures[i].node;
                if (ts_node_is_null(node)) continue;

                std::string node_text = get_node_text(node);
                uint32_t capture_name_len;
                const char* capture_name = ts_query_capture_name_for_id(
                    query, match.captures[i].index, &capture_name_len);
                
                if (strncmp(capture_name, "class", capture_name_len) == 0) {
                    def.type = "class";
                    def.definition = node_text;
                } else if (strncmp(capture_name, "function", capture_name_len) == 0) {
                    def.type = "function";
                    def.definition = node_text;
                } else if (strncmp(capture_name, "global", capture_name_len) == 0) {
                    def.type = "global";
                    def.definition = node_text;
                } else if (strncmp(capture_name, "name", capture_name_len) == 0) {
                    def.name = node_text;
                } else {
                    def.definition = node_text;
                }
            }

            if (!def.type.empty()) {
                definitions.push_back(def);
            }
        }

        ts_query_cursor_delete(cursor);
        ts_query_delete(query);

        return definitions;
    }

    // Helper function to process imports and track imported items
    void process_imports(const std::string& current_file, const std::vector<ImportDesc>& imports) {
        for (const auto& import : imports) {
            if (import.type == "import_from_statement") {
                bool is_relative = import.source.find('.') == 0;
                std::string imported_file = import_to_path(import.source, is_relative);
                
                if (!imported_file.empty()) {
                    // Add to dependency graph
                    add_dependency(current_file, imported_file);

                    // Track imported items
                    for (const auto& item : import.imports) {
                        ImportedItem imported_item;
                        imported_item.source_file = imported_file;
                        imported_item.original_name = item.import;
                        imported_item.name = item.alias.empty() ? item.import : item.alias;
                        imported_items[current_file].push_back(imported_item);
                    }
                }
            }
        }
    }

public:
    explicit ProjectContext(const std::string& root_path, bool verbose = false) 
        : project_root(std::filesystem::canonical(root_path)), verbose(verbose) {
        parser = ts_parser_new();
        ts_parser_set_language(parser, tree_sitter_python());
        current_tree = nullptr;
    }

    ~ProjectContext() {
        if (current_tree) ts_tree_delete(current_tree);
        if (parser) ts_parser_delete(parser);
    }

    void set_verbose(bool v) { verbose = v; }

    void add_file_imports(const std::string& file_path, const std::vector<ImportDesc>& imports) {
        file_imports[file_path] = imports;
    }

    void add_file_definitions(const std::string& file_path, const std::vector<FileDefinition>& definitions) {
        file_definitions[file_path] = definitions;
    }

    void add_dependency(const std::string& from, const std::string& to) {
        dependency_graph[from].insert(to);
    }

    void add_imported_item(const std::string& file_path, const ImportedItem& item) {
        imported_items[file_path].push_back(item);
    }

    unordered_json to_json() const{
        unordered_json project_json;
        
        // Add all file imports
        unordered_json imports_json;
        for (const auto& [file_path, imports] : file_imports) {
            unordered_json import_array = unordered_json::array();
            for (const auto& import : imports) {
                import_array.push_back(import.to_json());
            }
            imports_json[file_path] = import_array;
        }
        project_json["imports"] = imports_json;

        // Add all file definitions
        unordered_json definitions_json;
        for (const auto& [file_path, definitions] : file_definitions) {
            unordered_json def_array = unordered_json::array();
            for (const auto& def : definitions) {
                def_array.push_back(def.to_json());
            }
            definitions_json[file_path] = def_array;
        }
        project_json["definitions"] = definitions_json;

        // Add dependency graph
        unordered_json dep_json;
        for (const auto& [from, to_set] : dependency_graph) {
            dep_json[from] = json::array();
            for (const auto& to : to_set) {
                dep_json[from].push_back(to);
            }
        }
        project_json["dependencies"] = dep_json;

        // Add imported items information
        unordered_json imported_items_json;
        for (const auto& [file_path, items] : imported_items) {
            unordered_json items_array = unordered_json::array();
            for (const auto& item : items) {
                items_array.push_back(item.to_json());
            }
            imported_items_json[file_path] = items_array;
        }
        project_json["imported_items"] = imported_items_json;

        return project_json;
    }

    void save_to_file(const std::string& output_path) const {
        std::ofstream out_file(output_path);
        out_file << to_json().dump(2);
    }
    std::map<std::string, ImportedDefinition> get_imported_definitions(const std::string& file_name) const {
        std::map<std::string, ImportedDefinition> result;
        std::string abs_path = (project_root / file_name).string();
        
        if (!imported_items.count(abs_path)) return result;
        
        for (const auto& item : imported_items.at(abs_path)) {
            ImportedDefinition def;
            def.definition = find_definition(item.source_file, item.original_name);
            def.path = to_relative_path(item.source_file);
            
            if (!def.definition.empty()) {
                result[item.name] = def;
            }
        }
        
        return result;
    }

    unordered_json get_imported_definitions_json(const std::string& file_name) const {
        unordered_json result = unordered_json::array();
        auto definitions = get_imported_definitions(file_name);
        
        for (const auto& [name, def] : definitions) {
            result.push_back(def.to_json());
        }
        
        return result;
    }

    static std::shared_ptr<ProjectContext> build_project_context(const std::string& project_root, bool verbose = false) {
        auto context = std::make_shared<ProjectContext>(project_root, verbose);
        std::queue<std::string> files_to_process;
        std::set<std::string> processed_files;
        
        // Find all Python files in the project
        for (const auto& entry : std::filesystem::recursive_directory_iterator(project_root)) {
            if (entry.is_regular_file() && entry.path().extension() == ".py") {
                files_to_process.push(entry.path().string());
            }
        }

        while (!files_to_process.empty()) {
            std::string current_file = files_to_process.front();
            files_to_process.pop();

            if (processed_files.find(current_file) != processed_files.end()) {
                continue;
            }

            if (verbose) {
                std::cout << "Processing: " << current_file << std::endl;
            }

            try {
                const std::string source_code = read_file(std::filesystem::path(project_root) / current_file);
                context->parse_source(source_code);

                // Extract imports
                auto imports = context->extract_imports();
                context->add_file_imports(current_file, imports);

                // Process imports to track imported items and build dependency graph
                context->process_imports(current_file, imports);

                // Extract definitions
                auto definitions = context->extract_file_definitions();
                context->add_file_definitions(current_file, definitions);

                // Add imported files to processing queue if not already processed
                for (const auto& import : imports) {
                    if (import.type == "import_from_statement") {
                        bool is_relative = import.source.find('.') == 0;
                        std::string imported_file = context->import_to_path(import.source, is_relative);
                        if (!imported_file.empty() && processed_files.find(imported_file) == processed_files.end()) {
                            files_to_process.push(imported_file);
                        }
                    }
                }

                processed_files.insert(current_file);
            } catch (const std::exception& e) {
                if (verbose) {
                    std::cerr << "Error processing " << current_file << ": " << e.what() << std::endl;
                }
            }
        }

        return context;
    }
};