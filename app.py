from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file, session
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import time
import csv
import os
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        session['topic_name'] = request.form['topic_name']
        session['question_count'] = int(request.form['questions'])
        session['option_count'] = int(request.form['options'])
        return redirect(url_for('omr_sheet'))
    return render_template('home.html')

@app.route('/omr_sheet', methods=['GET', 'POST'])
def omr_sheet():
    if 'start_time' not in session:
        session['start_time'] = time.time()  # Start the timer when the OMR sheet is loaded
    
    if request.method == 'POST':
        question_count = session.get('question_count', 0)
        session['user_answers'] = [request.form.get(f'q{i}', '') for i in range(1, question_count + 1)]
        return redirect(url_for('correct_answers'))

    return render_template('omr_sheet.html', 
                           question_count=session.get('question_count', 0),
                           option_count=session.get('option_count', 0),
                           chr=chr)

@app.route('/correct_answers', methods=['GET', 'POST'])
def correct_answers():
    if request.method == 'POST':
        question_count = session.get('question_count', 0)
        session['correct_answers'] = [request.form.get(f'c{i}', '') for i in range(1, question_count + 1)]
        return redirect(url_for('results'))
    return render_template('correct_answers.html', 
                           question_count=session.get('question_count', 0),
                           option_count=session.get('option_count', 0),
                           chr=chr)

@app.route('/results')
def results():
    question_count = session.get('question_count', 0)
    user_answers = session.get('user_answers', [])
    correct_answers = session.get('correct_answers', [])
    
    correct_count = sum(1 for u, c in zip(user_answers, correct_answers) if u == c)
    wrong_count = sum(1 for u, c in zip(user_answers, correct_answers) if u and u != c)
    unattempted_count = sum(1 for u in user_answers if not u)
    accuracy = (correct_count / question_count) * 100 if question_count > 0 else 0

    # Convert total time taken to minutes and seconds
    total_time_taken = time.time() - session.get('start_time', 0)
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
    topic_name = session.get('topic_name', 'results')
    user_answers = session.get('user_answers', [])
    correct_answers = session.get('correct_answers', [])
    question_count = session.get('question_count', 0)

    csv_filename = f"{topic_name.replace(' ', '_')}_results.csv"
    csv_filepath = os.path.join(app.root_path, csv_filename)
    
    with open(csv_filepath, 'w', newline='') as csvfile:
        fieldnames = ['Question', 'Your Answer', 'Correct Answer']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(question_count):
            writer.writerow({
                'Question': i + 1,
                'Your Answer': user_answers[i] if i < len(user_answers) else "",
                'Correct Answer': correct_answers[i] if i < len(correct_answers) else ""
            })
    
    return send_from_directory(app.root_path, csv_filename, as_attachment=True)

@app.route('/download_pdf')
def download_pdf():
    topic_name = session.get('topic_name', 'results')
    user_answers = session.get('user_answers', [])
    correct_answers = session.get('correct_answers', [])
    question_count = session.get('question_count', 0)
    pdf_filename = f"{topic_name.replace(' ', '_')}_results.pdf"
    pdf_buffer = io.BytesIO()

    # Calculate the time taken
    total_time_taken = time.time() - session.get('start_time', 0)
    minutes = int(total_time_taken // 60)
    seconds = int(total_time_taken % 60)

    # Set up PDF document
    p = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter  # Page dimensions

    # Define colors and styles
    blue_color = colors.HexColor("#007bff")  # A pleasant blue shade
    p.setFillColor(blue_color)
    p.rect(0, height-100, width, 100, fill=True, stroke=False)  # Header only on the first page

    # Title in the header
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width/2, height-70, "OMR Sheet Results Report")

    # Reset color for body text
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 12)
    headers = ["Question", "Your Answer", "Correct Answer", "Correct?"]
    y = height-150
    x_positions = [70, 180, 320, 460]  # Column positions
    for i, header in enumerate(headers):
        p.drawString(x_positions[i], y, header)

    # Underline headers
    p.setStrokeColor(blue_color)
    p.line(70, y-2, width-70, y-2)

    # Table content
    p.setFont("Helvetica", 11)
    y -= 20
    for i in range(question_count):
        user_answer = user_answers[i] if i < len(user_answers) else "No answer"
        correct_answer = correct_answers[i] if i < len(correct_answers) else "No answer"
        correct = "Yes" if user_answer == correct_answer else "No"
        data = [f"Q{i + 1}", user_answer, correct_answer, correct]
        for j, item in enumerate(data):
            p.drawString(x_positions[j], y, item)
        y -= 20
        if y < 100:  # Ensure there's space for at least one line of statistics
            p.showPage()
            y = height - 100  # Reset y for new page

    # Add Statistics below the table
    p.setFont("Helvetica-Bold", 12)
    p.drawString(70, y - 20, "Statistics:")
    p.setFont("Helvetica", 11)
    p.drawString(70, y - 40, f"Total Questions: {question_count}")
    p.drawString(70, y - 60, f"Correct Answers: {sum(1 for u, c in zip(user_answers, correct_answers) if u == c)}")
    p.drawString(70, y - 80, f"Wrong Answers: {sum(1 for u, c in zip(user_answers, correct_answers) if u and u != c)}")
    p.drawString(70, y - 100, f"Unattempted Questions: {sum(1 for u in user_answers if not u)}")
    p.drawString(70, y - 120, f"Total Time Taken: {minutes}m {seconds}s")

    # Footer on the last page only
    p.setFillColor(blue_color)
    p.rect(0, 0, width, 50, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, 20, f"Generated by Digital OMR System")

    # Finish up and save the PDF
    p.showPage()
    p.save()

    # Move the buffer to the beginning so it can be read
    pdf_buffer.seek(0)

    # Send the PDF as a file attachment
    return send_file(pdf_buffer, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
