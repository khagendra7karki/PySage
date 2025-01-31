package main

import (
	"bufio"
	// "context"
	"encoding/json"
	"fmt"
	// "io"
	"os"
	// "os/exec"
	"path"
	"regexp"
	"strings"
	"sync"
	// "time"
)

type File struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

type Repo struct {
	RepoName string `json:"repo_name"`
	Files    []File `json:"files"`
}

func LoadData(dataPath string, chunkSize int) (<-chan []Repo, error) {
	f, err := os.Open(dataPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %w", err)
	}

	ch := make(chan []Repo, 1) // Buffered channel to avoid blocking

	go func() {
		defer f.Close()
		defer close(ch)

		reader := bufio.NewReader(f)
		var chunk []Repo

		for {
			line, err := reader.ReadString('\n') // Read line-by-line
			if err != nil {
				break // EOF or other read error
			}

			var repo Repo
			if err := json.Unmarshal([]byte(line), &repo); err != nil {
				fmt.Println("Failed to decode JSON line:", err)
				continue
			}

			chunk = append(chunk, repo)

			if len(chunk) >= chunkSize {
				ch <- chunk
				chunk = nil // Reset the chunk
			}
		}

		if len(chunk) > 0 {
			ch <- chunk
		}
	}()

	return ch, nil
}

// Regex patterns for Python code elements
var (
	// Matches triple quoted strings (both single and double quotes)
	tripleQuoteStringRegex = regexp.MustCompile(`"""([^"\\]|\\.)*"""|'''([^'\\]|\\.)*'''`)
	// Matches double quoted strings
	doubleQuoteStringRegex = regexp.MustCompile(`"([^"\\\n]|\\.)*"|'([^'\\\n]|\\.)*'`)

	// Matches comments
	// commentRegex = regexp.MustCompile(`(^[ \t]*#[^\n]*|[ \t]+#[^\n]*)`)

	// Matches non-English text using Unicode properties
	nonEnglishRegex = regexp.MustCompile(`[^\x00-\x7F]`)
)

// CleanPythonCode processes Python source code to:
// 1. Remove non-English comments
// 2. Replace non-English strings with placeholders
// 3. Preserve code structure and formatting
func CleanPythonCode(source string) string {
	// Process the code line by line
	var result []string
	lines := strings.Split(source, "\n")

	inMultilineString := false
	var multilineQuote string
	var multilineBuffer strings.Builder

	for _, line := range lines {
		if inMultilineString {
			multilineBuffer.WriteString(line + "\n")
			// Check if this line ends the multiline string
			if strings.Contains(line, multilineQuote) {
				// Process the complete multiline string
				fullStr := multilineBuffer.String()
				if nonEnglishRegex.MatchString(fullStr) {
					fullStr = multilineQuote + "STRING_PLACEHOLDER" + multilineQuote
				}
				result = append(result, fullStr)
				inMultilineString = false
				multilineBuffer.Reset()
				continue
			}
			continue
		}

		// Check for start of multiline strings
		if strings.Contains(line, `"""`) || strings.Contains(line, `'''`) {
			if strings.HasPrefix(strings.TrimSpace(line), `"""`) {
				inMultilineString = true
				multilineQuote = `"""`
				multilineBuffer.WriteString(line + "\n")
				continue
			}
			if strings.HasPrefix(strings.TrimSpace(line), `'''`) {
				inMultilineString = true
				multilineQuote = `'''`
				multilineBuffer.WriteString(line + "\n")
				continue
			}
		}

		// Process single line
		processedLine := processLine(line)
		result = append(result, processedLine)
	}

	return strings.Join(result, "\n")
}

// processLine handles a single line of code
func processLine(line string) string {
	// First handle comments
	commentStart := strings.Index(line, "#")
	if commentStart != -1 {
		beforeComment := line[:commentStart]
		comment := line[commentStart:]

		// Remove non-English comments
		if nonEnglishRegex.MatchString(comment) {
			return strings.TrimRight(beforeComment, " \t")
		}
		return line
	}

	// Handle single line triple-quoted strings
	if strings.Contains(line, `"""`) || strings.Contains(line, `'''`) {
		line = tripleQuoteStringRegex.ReplaceAllStringFunc(line, func(match string) string {
			if nonEnglishRegex.MatchString(match) {
				quotes := match[:3]
				return quotes + "STRING_PLACEHOLDER" + quotes
			}
			return match
		})
	}

	// Handle regular strings
	return doubleQuoteStringRegex.ReplaceAllStringFunc(line, func(match string) string {
		if nonEnglishRegex.MatchString(match) {
			return `"STRING_PLACEHOLDER"`
		}
		return match
	})
}

// IsNonEnglish checks if a string contains non-ASCII characters
func IsNonEnglish(s string) bool {
	return nonEnglishRegex.MatchString(s)
}

func WriteRepos(filePath string, repos []Repo) error {
	file, err := os.OpenFile(filePath,  os.O_WRONLY | os.O_CREATE | os.O_APPEND, 0666)
	if err != nil {
		return fmt.Errorf("openning write error %w", err)
	}
	defer file.Close()
	const WRITER_BUFFER_SIZE = 128 * 1024 * 1024 // 256 MB
	bufferedWriter := bufio.NewWriterSize(file, WRITER_BUFFER_SIZE)

	

	for _, repo := range repos {
		string_repo, err := json.Marshal(repo)
		if err != nil {
			return fmt.Errorf("marshalling json error%w", err)
		}
		bufferedWriter.Write(append(string_repo, byte(10)))



	}
	if err := bufferedWriter.Flush(); err != nil {
		return fmt.Errorf("while flushing the buffer %w", err)
	}


	return nil
}

func processFile(idx int, filePath, outFile, prefix string, chunkSize int) error {
	fmt.Printf("Processing file: %s\n", filePath) // Debugging statement
	repoStream, err := LoadData(filePath, chunkSize)
	if err != nil {
		return fmt.Errorf("loading data: %w", err)
	}

	// Process and send cleaned code to Python
	chunkCount := 0
	for chunk := range repoStream {
		for _, repo := range chunk {
			for _, file := range repo.Files {
				cleaned := CleanPythonCode(file.Content)
				file.Content = cleaned
			}
		}
		if err := WriteRepos(path.Join(outFile, fmt.Sprintf("%s_%d.jsonl", prefix, idx)), chunk); err != nil {
			return fmt.Errorf("writing error %w", err)
		}
		chunkCount += 1
	}

	return nil
}


func main() {
	fmt.Println("Starting the program")
	codeDir := "../../../python-dataset/normalized_data"
	outDir := "../../../python-dataset/cleaned_data"
	entries, err := os.ReadDir(codeDir)
	if err != nil {
		fmt.Printf("Error reading direcotry %v\n", err)
	}



	var wg sync.WaitGroup
	for i, file := range entries {
		wg.Add(1)
		go func(idx int, fileName string) {
			defer wg.Done()
			if err := processFile(i, path.Join(codeDir, fileName),
				outDir, "data", 3000); err != nil {
				fmt.Printf("Error Processing file %s: %v\n", fileName, err)
			}
		}(i, file.Name())
	}
	wg.Wait()

}
