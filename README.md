# HyperSpeedGrader
AI-assisted grading CLI for any Canvas course.

Overview:
* You specify how grading criteria for a task and which task we are grading (see [Usage](#Usage))
* You optionally specify a list of students to grade
* Script gets student answers from Canvas using API
* Then for each student does the following:
	* Sends [prompt](./configs/prompt.txt), [grading criteria](./configs/task.txt) and student answer to OpenAI compatible model
	* Gets grade and a comment
	* Prompts you to accept/edit/skip result

Features:
* Skips already graded and empty answers
* Can work in "full-auto" mode without prompting user ever

## Usage
0. Clone project
```sh
git clone https://github.com/Gunter-Q12/hyper-speed-grader.git
cd hyper-speed-grader
```
1. Install requirements
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Create `.env` file with secrets
```sh
# Get canvas api key here: https://canvas.instructure.com/profile/settings
export CANVAS_API_KEY=<your_token>

# Set a token of OpenAI compatible model
# Tested with Deepseed
export OPENAI_API_KEY=<your_token>
# Set base URL if you not using OpenAI itself
export OPENAI_BASE_URL=https://api.deepseek.com
# Set model to use
export OPENAI_MODEL=deepseek-chat

# Go your course and copy ID form URL
export CANVAS_COURSE_ID=13080964  # This is "НИС РС" course ID
export CANVAS_API_URL=https://canvas.instructure.com
```
3. Edit configs
	1. Provide task and how answer should be graded in file [./configs/task.txt](./configs/task.txt). Check current contents for an example
	2. (Optional) If you want to grade only some subset of users, edit [./configs/students.csv](./configs/students.csv). You can copy student names from Canvas site or run `python3 ./users.py`
	3. (Optional) To tweak prompt edit [./configs/prompt.txt](./configs/prompt.txt)
4. Source `.env` file and run HyperSpeedGrader:
```sh
source .env
python3 ./main.py -h  # Run help for avaialble options
python3 ./main.py --prompt configs/prompt.txt \
    --task configs/task.txt --task-num 2 \
    --students configs/students.csv \
    --confirmation full --dry-run
```
