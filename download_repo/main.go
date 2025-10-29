package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
	"net/url"
	"strconv"
)

// Repository represents the GitHub repository structure
type Repository struct {
	Name     string `json:"name"`
	CloneURL string `json:"clone_url"`
}

// GitHub API response structure
type GitHubResponse struct {
	Items []Repository `json:"items"`
}

// Define the structure for our output
type PyFile struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

type RepoData struct {
	RepoName string   `json:"repo_name"`
	Files    []PyFile `json:"files"`
}

// ProgressState tracks which repositories have been processed
type ProgressState struct {
	ProcessedRepos  map[string]bool `json:"processed_repos"`
	LastDateChecked string          `json:"last_date_checked"`
}

// Helper function for min
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// SaveProgress saves the current progress to a JSON file
func saveProgress(progressFile string, processed map[string]bool, lastDate string) error {
	state := ProgressState{
		ProcessedRepos:  processed,
		LastDateChecked: lastDate,
	}
	
	data, err := json.Marshal(state)
	if err != nil {
		return fmt.Errorf("error marshaling progress: %v", err)
	}
	
	return ioutil.WriteFile(progressFile, data, 0644)
}

// LoadProgress loads the previous progress from a JSON file
func loadProgress(progressFile string) (map[string]bool, string, error) {
	// If file doesn't exist, return empty state
	if _, err := os.Stat(progressFile); os.IsNotExist(err) {
		return make(map[string]bool), "", nil
	}
	
	data, err := ioutil.ReadFile(progressFile)
	if err != nil {
		return nil, "", fmt.Errorf("error reading progress file: %v", err)
	}
	
	var state ProgressState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, "", fmt.Errorf("error unmarshaling progress: %v", err)
	}
	
	if state.ProcessedRepos == nil {
		state.ProcessedRepos = make(map[string]bool)
	}
	
	return state.ProcessedRepos, state.LastDateChecked, nil
}

func fetchAllRepos(language, startDate, endDate string, token string, lastProcessedDate string) ([]Repository, error) {
	// Parse the date range
	var start time.Time
	var err error
	
	if lastProcessedDate != "" {
		// Resume from the last processed date
		start, err = time.Parse("2006-01-02", lastProcessedDate)
		if err != nil {
			return nil, fmt.Errorf("invalid last processed date: %v", err)
		}
	} else {
		// Start from the beginning
		start, err = time.Parse("2006-01-02", startDate)
		if err != nil {
			return nil, fmt.Errorf("invalid start date: %v", err)
		}
	}
	
	end, err := time.Parse("2006-01-02", endDate)
	if err != nil {
		return nil, fmt.Errorf("invalid end date: %v", err)
	}
	
	allRepos := []Repository{}
	currentStart := start
	
	// Create smaller date ranges to stay under GitHub's 1,000 result limit
	for currentStart.Before(end) {
		// Try with a 7-day window first
		currentEnd := currentStart.AddDate(0, 0, 7)
		if currentEnd.After(end) {
			currentEnd = end
		}
		
		startStr := currentStart.Format("2006-01-02")
		endStr := currentEnd.Format("2006-01-02")
		
		fmt.Printf("Fetching repos for date range: %s to %s\n", startStr, endStr)
		query := fmt.Sprintf("language:%s created:%s..%s", language, startStr, endStr)
		repos, count, err := fetchReposInDateRange(query, token)
		
		if err != nil {
			// Save the current date before exiting so we can resume from here
			fmt.Printf("Error occurred at date %s: %v\n", startStr, err)
			return allRepos, fmt.Errorf("error at date %s: %v", startStr, err)
		}
		
		// If we got close to 1000 results, we need to make the date range smaller
		if count >= 900 {
			// Try with a smaller window (e.g., 1 day at a time)
			subStart := currentStart
			for subStart.Before(currentEnd) {
				subEnd := subStart.AddDate(0, 0, 1)
				if subEnd.After(currentEnd) {
					subEnd = currentEnd
				}
				
				subStartStr := subStart.Format("2006-01-02")
				subEndStr := subEnd.Format("2006-01-02")
				
				fmt.Printf("Fetching repos for smaller range: %s to %s\n", subStartStr, subEndStr)
				subQuery := fmt.Sprintf("language:%s created:%s..%s", language, subStartStr, subEndStr)
				subRepos, _, subErr := fetchReposInDateRange(subQuery, token)
				
				if subErr != nil {
					// Save the current date before exiting so we can resume from here
					fmt.Printf("Error occurred at date %s: %v\n", subStartStr, subErr)
					return allRepos, fmt.Errorf("error at date %s: %v", subStartStr, subErr)
				}
				
				allRepos = append(allRepos, subRepos...)
				subStart = subEnd
			}
		} else {
			// We got fewer than 900 results, so we can safely add them
			allRepos = append(allRepos, repos...)
		}
		
		currentStart = currentEnd
	}
	
	return allRepos, nil
}

func fetchReposInDateRange(query string, token string) ([]Repository, int, error) {
	baseURL := "https://api.github.com/search/repositories?q=" + url.QueryEscape(query) + "&per_page=100&page="
	client := &http.Client{}
	
	// Make an initial request to get the total count
	req, err := http.NewRequest("GET", baseURL+"1", nil)
	if err != nil {
		return nil, 0, err
	}
	
	req.Header.Set("Authorization", "token "+token)
	req.Header.Set("Accept", "application/vnd.github.v3+json")
	
	resp, err := client.Do(req)
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()
	
	// Check for rate limiting
	if resp.StatusCode == http.StatusForbidden {
		rateLimitReset := resp.Header.Get("X-RateLimit-Reset")
		resetTime, err := strconv.ParseInt(rateLimitReset, 10, 64)
		if err == nil {
			waitTime := time.Unix(resetTime, 0).Sub(time.Now())
			return nil, 0, fmt.Errorf("rate limit exceeded, reset in %v (at %s)", 
				waitTime, time.Unix(resetTime, 0).Format(time.RFC3339))
		}
		return nil, 0, fmt.Errorf("rate limit exceeded")
	}
	
	if resp.StatusCode != http.StatusOK {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, 0, fmt.Errorf("GitHub API error: %s - %s", resp.Status, string(body))
	}
	
	var result GitHubResponse
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, 0, err
	}
	
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, 0, err
	}
	
	totalCount := len(result.Items)
	repos := result.Items
	
	// Only fetch additional pages if we have more results
	if totalCount > 100 {
		maxPages := min(10, (totalCount+99)/100) // GitHub limits to 1000 results (10 pages of 100)
		
		for page := 2; page <= maxPages; page++ {
			time.Sleep(time.Second) // Rate limiting
			
			req, err := http.NewRequest("GET", baseURL+fmt.Sprintf("%d", page), nil)
			if err != nil {
				return nil, 0, err
			}
			
			req.Header.Set("Authorization", "token "+token)
			req.Header.Set("Accept", "application/vnd.github.v3+json")
			
			resp, err := client.Do(req)
			if err != nil {
				return nil, 0, err
			}
			
			// Check for rate limiting
			if resp.StatusCode == http.StatusForbidden {
				resp.Body.Close()
				rateLimitReset := resp.Header.Get("X-RateLimit-Reset")
				resetTime, err := strconv.ParseInt(rateLimitReset, 10, 64)
				if err == nil {
					waitTime := time.Unix(resetTime, 0).Sub(time.Now())
					return nil, 0, fmt.Errorf("rate limit exceeded, reset in %v (at %s)", 
						waitTime, time.Unix(resetTime, 0).Format(time.RFC3339))
				}
				return nil, 0, fmt.Errorf("rate limit exceeded")
			}
			
			body, err := ioutil.ReadAll(resp.Body)
			resp.Body.Close()
			
			if err != nil {
				return nil, 0, err
			}
			
			if resp.StatusCode != http.StatusOK {
				return nil, 0, fmt.Errorf("GitHub API error: %s - %s", resp.Status, string(body))
			}
			
			var pageResult GitHubResponse
			if err := json.Unmarshal(body, &pageResult); err != nil {
				return nil, 0, err
			}
			
			repos = append(repos, pageResult.Items...)
		}
	}
	
	return repos, totalCount, nil
}

// This function extracts Python files from a repository and saves them to a JSONL file
func extractPythonFiles(repoPath, outputPath string) error {
	// Get the repository name from the path
	repoName := filepath.Base(repoPath)
	
	// Use the collectPythonFiles function to get all Python files
	pythonFilePaths, err := collectPythonFiles(repoPath)
	if err != nil {
		return fmt.Errorf("error collecting Python files: %v", err)
	}
	
	// Process each Python file
	var pythonFiles []PyFile
	for _, path := range pythonFilePaths {
		// Get the relative path from the repo root
		relPath, err := filepath.Rel(repoPath, path)
		if err != nil {
			return fmt.Errorf("error getting relative path: %v", err)
		}
		
		// Read file content
		content, err := ioutil.ReadFile(path)
		if err != nil {
			fmt.Printf("Warning: Could not read file %s: %v\n", path, err)
			continue
		}
		
		// Add to our slice
		pythonFiles = append(pythonFiles, PyFile{
			Path:    relPath,
			Content: string(content),
		})
	}
	
	// Create the repo data structure
	repoData := RepoData{
		RepoName: repoName,
		Files:    pythonFiles,
	}
	
	// Open the output file for writing
	file, err := os.OpenFile(outputPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("error opening output file: %v", err)
	}
	defer file.Close()
	
	// Marshal to JSON and write to file
	jsonData, err := json.Marshal(repoData)
	if err != nil {
		return fmt.Errorf("error marshaling JSON: %v", err)
	}
	
	// Write line to file
	if _, err := file.Write(jsonData); err != nil {
		return fmt.Errorf("error writing to file: %v", err)
	}
	
	// Add newline
	if _, err := file.Write([]byte("\n")); err != nil {
		return fmt.Errorf("error writing newline: %v", err)
	}
	
	fmt.Printf("Processed repo %s: found %d Python files\n", repoName, len(pythonFiles))
	return nil
}

func cloneRepo(repo Repository, outputDir string, wg *sync.WaitGroup, retries int, idx int, processed map[string]bool, progressMutex *sync.Mutex, progressFile, lastDate string) {
	defer wg.Done()
	
	// Check if already processed
	progressMutex.Lock()
	if processed[repo.Name] {
		fmt.Printf("Skipping already processed repo: %s\n", repo.Name)
		progressMutex.Unlock()
		return
	}
	progressMutex.Unlock()
	
	repoPath := filepath.Join(outputDir, repo.Name)
	fmt.Printf("Cloning %s...\n", repo.Name)
	
	success := false
	for i := 0; i < retries && !success; i++ {
		cmd := exec.Command("git", "clone", "--depth", "1", repo.CloneURL, repoPath)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		
		if err := cmd.Run(); err != nil {
			fmt.Printf("Failed to clone %s (attempt %d/%d): %v\n", repo.Name, i+1, retries+1, err)
			if i < retries {
				time.Sleep(time.Duration(i+1) * time.Second)
			} else {
				fmt.Printf("Giving up on %s after %d attempts\n", repo.Name, retries+1)
			}
		} else {
			success = true
		}
	}
	
	if success {
		if err := extractPythonFiles(repoPath, fmt.Sprintf("filtered_python_file_%d_.jsonl", idx)); err != nil {
			fmt.Printf("Error processing repo %s: %v\n", repo.Name, err)
		}
		
		// Mark as processed and save progress
		progressMutex.Lock()
		processed[repo.Name] = true
		err := saveProgress(progressFile, processed, lastDate)
		if err != nil {
			fmt.Printf("Warning: Failed to save progress: %v\n", err)
		}
		progressMutex.Unlock()
	}
	
	if err := os.RemoveAll(repoPath); err != nil {
		fmt.Printf("Error removing the directory %s: %v\n", repo.Name, err)
	}
}

func collectPythonFiles(rootDir string) ([]string, error) {
	var pythonFiles []string
	err := filepath.Walk(rootDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(path, ".py") {
			pythonFiles = append(pythonFiles, path)
		}
		return nil
	})
	
	return pythonFiles, err
}

func main() {
	createdAfter := "2025-03-04"
	endDate := "2025-04-20"
	outputDir := "./scraped_repos"
	progressFile := "./progress.json"
	apiToken := os.Getenv("GITHUB_ACCESS_TOKEN") // Use GitHub token from environment variable
	
	if apiToken == "" {
		fmt.Println("Error: GITHUB_TOKEN environment variable not set")
		return
	}
	
	os.MkdirAll(outputDir, os.ModePerm)
	
	// Load progress from previous run
	processedRepos, lastDate, err := loadProgress(progressFile)
	if err != nil {
		fmt.Printf("Error loading progress: %v. Starting from scratch.\n", err)
		processedRepos = make(map[string]bool)
		lastDate = ""
	}
	
	if lastDate != "" {
		fmt.Printf("Resuming from date: %s\n", lastDate)
	} else {
		fmt.Printf("Starting new scan from date: %s\n", createdAfter)
		lastDate = createdAfter
	}
	
	// Fetch repositories
	repos, err := fetchAllRepos("python", createdAfter, endDate, apiToken, lastDate)
	if err != nil {
		fmt.Println("Error fetching repositories:", err)
		
		// Check if we made any progress
		if len(repos) > 0 {
			fmt.Printf("Fetched %d repositories before error occurred.\n", len(repos))
		} else {
			return
		}
	}
	
	fmt.Printf("Found %d repositories to process\n", len(repos))
	
	// Filter out already processed repos
	var reposToProcess []Repository
	for _, repo := range repos {
		if !processedRepos[repo.Name] {
			reposToProcess = append(reposToProcess, repo)
		}
	}
	
	fmt.Printf("%d repositories need processing (skipping %d already processed)\n", 
		len(reposToProcess), len(repos)-len(reposToProcess))
	
	var wg sync.WaitGroup
	semaphore := make(chan struct{}, 5) // Limit to 5 concurrent clones
	var progressMutex sync.Mutex
	
	for idx, repo := range reposToProcess {
		wg.Add(1)
		semaphore <- struct{}{}
		
		// Calculate the current date being processed for saving progress
		currentDate := lastDate
		
		go func(repo Repository, idx int) {
			cloneRepo(repo, outputDir, &wg, 3, idx%5, processedRepos, &progressMutex, progressFile, currentDate)
			<-semaphore
		}(repo, idx)
	}
	
	wg.Wait()
	fmt.Println("Cloning and file collection completed!")
	
	// Save final progress
	if err := saveProgress(progressFile, processedRepos, endDate); err != nil {
		fmt.Printf("Error saving final progress: %v\n", err)
	}
}
