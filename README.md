# quiz-nt

# Description

  "quiz-nt" est une application web conçue pour créer, gérer et jouer à des quiz interactifs qui a été développé avec le framework Flask.
  L'objectif principal de ce projet est de fournir une plateforme simple et accessible pour les utilisateurs, leur permettant de tester leurs connaissances sur différents sujets.

# Fonctionnalités

  - Création de quiz personnalisés.
  - Participation aux quiz.
  - Affichage des scores.
  - Intégration facile avec Azure pour le déploiement.

# Structure du projet

  - "app.py" : Le fichier principal contenant la logique backend de l'application.
  - "templates/" : Contient les fichiers HTML pour l'interface utilisateur.
  - "static/" : Contient le fichier CSS pour le style.
  - "requirements.txt" : Liste des dépendances Python nécessaires au projet.


# Déploiement du projet

  - Clonez le dépôt: git clone https://github.com/nic0119/quiz-nt.git
  - Accédez à votre dossier: cd <nom-de-votre-dossier>
  - Installez les bibliothèques Python nécessaires: pip install -r requirements.txt
  - Configurez un fichier .env avec cette architecture:
        ```
        SQLALCHEMY_DATABASE_URI=<votre_chaine_de_connection_base_de_donnees>
        AZURE_STORAGE_CONNECTION_STRING=<votre_chaine_de_connection_blob_storage>
        SECRET_KEY=<votre_cle_secrete>
        ```
  - Lancez l'application localement: python app.py
