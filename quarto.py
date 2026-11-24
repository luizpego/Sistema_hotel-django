class Quarto:
    def __init__(self, tipo, valor_diaria, numero, status='desocupado', valor_mensal=0,
                 capacidade=1, banheiro=False):
        self.tipo = tipo
        self.numero = numero
        self.valor_diaria = valor_diaria
        self.status = status
        self.valor_mensal = valor_mensal
        self.capacidade = capacidade
        self.banheiro = banheiro


    def verificar_status(self):
        if self.status.lower() == 'ocupado':
            return 1
        return 0


    def get_valor_mensal(self):
        return self.valor_mensal


    def get_valor_diaria(self):
        return self.valor_diaria


    def get_numero(self):
        return self.numero


    def get_tipo(self):
        return self.tipo

    def set_status(self, status):
        self.status = status
