from flask import Flask, render_template, request, redirect, url_for
import pyodbc
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration de l'application Flask
app.config['SECRET_KEY'] = 'my_secret_key'

# Configuration pour l'upload des fichiers
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Crée le dossier si inexistant

# Configuration environnement Azure
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client("images")

# Connexion à la base de données via pyodbc
conn_str = os.getenv('DATABASE_CONNECTION_STRING')
connection = pyodbc.connect(conn_str)

# Routes de l'application
@app.route('/')
def index():
    cursor = connection.cursor()
    cursor.execute("SELECT id, title FROM Quiz")
    quizzes = cursor.fetchall()
    return render_template('index.html', quizzes=quizzes)


@app.route('/create-quiz', methods=['GET', 'POST'])
def create_quiz():
    if request.method == 'POST':
        # Récupération des données du formulaire
        title = request.form.get('title')
        questions = request.form.getlist('question')
        answers = request.form.getlist('answer')
        images = request.files.getlist('image')

        # Validation des données
        if not title or not questions or not answers:
            return "Formulaire incomplet. Veuillez remplir tous les champs.", 400

        cursor = connection.cursor()

        # Création du quiz
        cursor.execute("INSERT INTO Quiz (title) VALUES (?)", (title,))
        connection.commit()
        quiz_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]

        # Ajout des questions
        for i, (question_text, correct_answer) in enumerate(zip(questions, answers)):
            image_file = images[i] if i < len(images) else None
            image_filename = None

            # Gestion de l'upload de l'image
            if image_file and image_file.filename:
                blob_name = f"quiz_{quiz_id}_q{i}_{image_file.filename}"
                blob_client = container_client.get_blob_client(blob_name)
                blob_client.upload_blob(image_file, overwrite=True)
                image_filename = blob_name

            # Ajout de la question à la base
            cursor.execute(
                "INSERT INTO Question (quiz_id, question_text, correct_answer, image_filename) VALUES (?, ?, ?, ?)",
                (quiz_id, question_text, correct_answer, image_filename),
            )
        connection.commit()

        return redirect(url_for('index'))

    return render_template('create_quiz.html')


@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def quiz(quiz_id):
    cursor = connection.cursor()
    quiz = cursor.execute("SELECT id, title FROM Quiz WHERE id = ?", (quiz_id,)).fetchone()
    questions = cursor.execute("SELECT id, question_text, correct_answer FROM Question WHERE quiz_id = ?", (quiz_id,)).fetchall()

    if request.method == 'POST':
        pseudo = request.form.get('pseudo')
        if not pseudo:
            return "Veuillez entrer un pseudo pour continuer.", 400

        score = 0
        for question in questions:
            user_answer = request.form.get(str(question.id))
            if user_answer and user_answer.strip().lower() == question.correct_answer.strip().lower():
                score += 1

        # Sauvegarde du score dans la base
        cursor.execute(
            "INSERT INTO Score (quiz_id, pseudo, user_score) VALUES (?, ?, ?)",
            (quiz_id, pseudo, score),
        )
        connection.commit()

        return redirect(url_for('result', quiz_id=quiz_id, score=score, pseudo=pseudo))

    return render_template('quiz.html', quiz=quiz, questions=questions)


@app.route('/result/<int:quiz_id>/<int:score>')
def result(quiz_id, score):
    pseudo = request.args.get('pseudo', 'Inconnu')
    cursor = connection.cursor()
    quiz = cursor.execute("SELECT id, title FROM Quiz WHERE id = ?", (quiz_id,)).fetchone()
    return render_template('result.html', quiz=quiz, score=score, pseudo=pseudo)


@app.route('/scores/<int:quiz_id>')
def scores(quiz_id):
    cursor = connection.cursor()
    quiz = cursor.execute("SELECT id, title FROM Quiz WHERE id = ?", (quiz_id,)).fetchone()
    scores = cursor.execute("SELECT pseudo, user_score FROM Score WHERE quiz_id = ?", (quiz_id,)).fetchall()
    return render_template('scores.html', quiz=quiz, scores=scores)


if __name__ == '__main__':
    with app.app_context():
        # Crée les tables si elles n'existent pas déjà (à faire manuellement ici si nécessaire)
        cursor = connection.cursor()
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Quiz' AND xtype='U')
        CREATE TABLE Quiz (
            id INT PRIMARY KEY IDENTITY(1,1),
            title NVARCHAR(100) NOT NULL
        )""")
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Question' AND xtype='U')
        CREATE TABLE Question (
            id INT PRIMARY KEY IDENTITY(1,1),
            quiz_id INT FOREIGN KEY REFERENCES Quiz(id),
            question_text NVARCHAR(500) NOT NULL,
            correct_answer NVARCHAR(100) NOT NULL,
            image_filename NVARCHAR(200)
        )""")
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Score' AND xtype='U')
        CREATE TABLE Score (
            id INT PRIMARY KEY IDENTITY(1,1),
            quiz_id INT FOREIGN KEY REFERENCES Quiz(id),
            pseudo NVARCHAR(100) NOT NULL,
            user_score INT NOT NULL
        )""")
        connection.commit()

    app.run(host="0.0.0.0", debug=True)
