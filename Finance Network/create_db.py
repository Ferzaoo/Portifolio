from app import app, db

with app.app_context():
    db.drop_all()  # Remove todas as tabelas
    db.create_all()  # Cria as tabelas novamente
