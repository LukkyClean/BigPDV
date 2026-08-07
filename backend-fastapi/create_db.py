from app.db.migrations import aplicar_migracoes

if __name__ == "__main__":
    print("Criando tabelas no banco de dados via Alembic...")
    aplicar_migracoes()
    print("Banco de dados criado com sucesso!")
