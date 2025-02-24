# Receipt LLM Categorizer
A script that extracts text from a scanned receipt, turns it into text, and sends to LLM for it to process the transactions into different budget categories.

## Why
OpenAI and other LLMs are pretty good at interpreting data given, but not the best when the format is a binary image or PDF without OCR pre-processed. The goal of this script is to use open source tools already available to pre-process a recepit into raw text that is cleaned up so each receipt item is consistently send to the LLM line by line without having superfloulus characters prefixing and suffixing each line of the receipt. 

I am also sure there are some ways of using Ollama to run this locally, and I'm sure I'm being stupid by giving OpenAI my receipt data, but I also intend to write in functions that would anonomyze the receipt if you give it environment variables for things like "name" and "membership id" or "account number" or what the last few digits of your credit card is (which is obviously run locally on your machine before sending it to datagobblers).

## Pre-reqs
Stuff

## Other
Stuff
