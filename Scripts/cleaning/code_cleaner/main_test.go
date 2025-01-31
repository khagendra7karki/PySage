package main

import (
	"fmt"
	"os"
	// "path"
	// "sync"

	// "io"
	// "regexp"
	// "os/exec"
	"testing"
)

func TestMain(m *testing.M){
// 	code := `
// a="hello world" # """okay lets check this新竹市[xīnzhúshì]"

// c = "lets see if our code recognizes this" #""" another python comment`

	// repoStream, err := LoadData(codeDir, chunk_size)
	// codeDir := "../../../python-dataset/normalized_data"
	// entries, err := os.ReadDir(codeDir)
	// if err != nil {
	// 	fmt.Printf("Error reading direcotry %v\n", err)
	// }
	
	// var wg sync.WaitGroup
	// for i, file := range entries {
	// 	wg.Add(1)
	// 	go func(idx int, fileName string) {
	// 		defer wg.Done()
	// 		repoStream, err := LoadData(path.Join(codeDir, fileName),  3000)
	// 		if err != nil {
	// 			fmt.Printf("Error while creatting data loader strea %s", err)
	// 			return
	// 		}

	// 		// Process and send cleaned code to Python
	// 		chunkCount := 0
	// 		for range repoStream {
	// 			fmt.Printf("Chunk %d processing from file path: %s\n", chunkCount, fileName)
	// 			chunkCount++
	// 		}


	// 	}(i, file.Name())
	// }
	// wg.Wait()

	codePath := "../../../nonenglish.py"

	byteContent, err := os.ReadFile(codePath)
	if err != nil {
		fmt.Println("An error occurred while readubg the file")
	}


	stringContent := string(byteContent)


	cleaned := CleanPythonCode(stringContent)

	file, err := os.OpenFile("../../../cleaned_nonenglish.py", os.O_WRONLY | os.O_CREATE, 0666)
	if err != nil {
		fmt.Println("An error occurred while writing the file")
	}

	file.Write([]byte(cleaned))
}