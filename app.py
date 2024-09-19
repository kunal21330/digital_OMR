from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import time
import csv
import os

app = Flask(__name__)

# Global variables to hold OMR data
topic_name = ""
question_count = 0
option_count = 0
user_answers = []
correct_answers = []
start_time = 0

@app.route('/', methods=['GET', 'POST'])
def home():
    global topic_name, question_count, option_count
    if request.method == 'POST':
        topic_name = request.form['topic_name']
        question_count = int(request.form['questions'])
        option_count = int(request.form['options'])
        return redirect(url_for('omr_sheet'))
    return render_template('home.html')


@app.route('/omr_sheet', methods=['GET', 'POST'])
def omr_sheet():
    global start_time
    if request.method == 'POST':
        global user_answers, option_count
        user_answers = [request.form.get(f'q{i}', '') for i in range(1, question_count + 1)]
        total_time_taken = time.time() - start_time
        return redirect(url_for('correct_answers'))
    
    start_time = time.time()  # Start the timer when the OMR sheet is loaded
    return render_template('omr_sheet.html', question_count=question_count, option_count=option_count, chr=chr)

@app.route('/correct_answers', methods=['GET', 'POST'])
def correct_answers():
    if request.method == 'POST':
        global correct_answers
        correct_answers = [request.form.get(f'c{i}', '') for i in range(1, question_count + 1)]
        return redirect(url_for('results'))
    return render_template('correct_answers.html', question_count=question_count, option_count=option_count, chr=chr)

@app.route('/results')
def results():
    global user_answers, correct_answers, question_count, start_time
    correct_count = sum(1 for u, c in zip(user_answers, correct_answers) if u == c)
    wrong_count = sum(1 for u, c in zip(user_answers, correct_answers) if u and u != c)
    unattempted_count = sum(1 for u in user_answers if not u)
    accuracy = (correct_count / question_count) * 100 if question_count > 0 else 0

    # Convert total time taken to minutes and seconds
    total_time_taken = time.time() - start_time
    minutes = int(total_time_taken // 60)
    seconds = int(total_time_taken % 60)

    return render_template(
        'results.html',
        question_count=question_count,
        correct_count=correct_count,
        wrong_count=wrong_count,
        unattempted_count=unattempted_count,
        accuracy=f"{accuracy:.2f}",
        minutes=minutes,
        seconds=seconds
    )

@app.route('/download_results')
def download_results():
    global topic_name, user_answers, correct_answers, question_count, start_time
    csv_filename = f"{topic_name.replace(' ', '_')}_results.csv"
    csv_filepath = os.path.join(app.root_path, csv_filename)
    with open(csv_filepath, 'w', newline='') as csvfile:
        fieldnames = ['Question', 'Your Answer', 'Correct Answer']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(question_count):
            writer.writerow({
                'Question': i + 1,
                'Your Answer': user_answers[i],
                'Correct Answer': correct_answers[i]
            })
    
    return send_from_directory(app.root_path, csv_filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
