class Funcionario:
    def __init__(self, nome, cpf, telefone, cargo):
        self.nome = nome
        self.cpf = cpf
        self.telefone = telefone
        self.cargo = cargo

    def get_nome(self):
        return self.nome

    def get_cargo(self):
        return self.cargo
