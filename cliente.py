class Cliente:
    def __init__(self, nome, cpf, telefone, nascimento=None, email=''):
        self.nome = nome
        self.cpf = cpf
        self.telefone = telefone
        self.nascimento = nascimento
        self.email = email
    def get_nome(self):
        return self.nome

    def get_telefone(self):
        return self.telefone

    def get_cpf(self):
        return self.cpf
