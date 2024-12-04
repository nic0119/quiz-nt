from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


load_dotenv()
# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration de l'application Flask
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'my_secret_key'

# Configuration pour l'upload des fichiers
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Crée le dossier si inexistant

# Configuration environnement azure
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client("images")

# Initialisation de la base de données SQLAlchemy
db = SQLAlchemy(app)


# Modèles pour la base de données
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)  # Nom du fichier image


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    pseudo = db.Column(db.String(100), nullable=False)
    user_score = db.Column(db.Integer, nullable=False)


# Routes de l'application

@app.route('/')
def index():
    quizzes = Quiz.query.all()
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

        # Création du quiz
        new_quiz = Quiz(title=title)
        db.session.add(new_quiz)
        db.session.commit()

        # Ajout des questions
        for i, (question_text, correct_answer) in enumerate(zip(questions, answers)):
            image_file = images[i] if i < len(images) else None
            image_filename = None

            # Gestion de l'upload de l'image
            if image_file and image_file.filename:
                blob_name = f"quiz_{new_quiz.id}_q{i}_{image_file.filename}"
                blob_client = container_client.get_blob_client(blob_name)
                blob_client.upload_blob(image_file, overwrite=True)
                image_filename = blob_name 

            # Création de la question
            question = Question(
                quiz_id=new_quiz.id,
                question_text=question_text,
                correct_answer=correct_answer,
                image_filename=image_filename
            )
            db.session.add(question)
        db.session.commit()

        return redirect(url_for('index'))

    # Affichage du formulaire pour GET
    return render_template('create_quiz.html')


@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    if request.method == 'POST':
        pseudo = request.form.get('pseudo')
        if not pseudo:
            return "Veuillez entrer un pseudo pour continuer.", 400

        score = 0
        for question in questions:
            user_answer = request.form.get(str(question.id))
            if user_answer and user_answer.strip().lower() == question.correct_answer.strip().lower():
                score += 1

        # Sauvegarde du score dans la base de données
        new_score = Score(quiz_id=quiz_id, pseudo=pseudo, user_score=score)
        db.session.add(new_score)
        db.session.commit()

        return redirect(url_for('result', quiz_id=quiz_id, score=score, pseudo=pseudo))

    return render_template('quiz.html', quiz=quiz, questions=questions)


@app.route('/result/<int:quiz_id>/<int:score>')
def result(quiz_id, score):
    pseudo = request.args.get('pseudo', 'Inconnu')
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('result.html', quiz=quiz, score=score, pseudo=pseudo)


@app.route('/scores/<int:quiz_id>')
def scores(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    scores = Score.query.filter_by(quiz_id=quiz_id).all()
    return render_template('scores.html', quiz=quiz, scores=scores)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Recrée toutes les tables
    app.run(debug=True, host='127.0.0.1', port=5000)
