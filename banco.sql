-- MySQL 8.0.16+. Execute dentro de um banco vazio com charset utf8mb4.
CREATE TABLE IF NOT EXISTS clientes (
 id INT AUTO_INCREMENT PRIMARY KEY, nome VARCHAR(100) NOT NULL,
 cpf CHAR(11) NOT NULL UNIQUE, telefone VARCHAR(11) NOT NULL,
 nascimento DATE NULL, email VARCHAR(100) NOT NULL DEFAULT '',
 ativo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS quartos (
 id INT AUTO_INCREMENT PRIMARY KEY, numero INT NOT NULL UNIQUE,
 tipo VARCHAR(30) NOT NULL, valor_diaria DECIMAL(10,2) NOT NULL,
 valor_mensal DECIMAL(10,2) NOT NULL DEFAULT 0, capacidade INT NOT NULL DEFAULT 1,
 banheiro BOOLEAN NOT NULL DEFAULT FALSE,
 status VARCHAR(20) NOT NULL DEFAULT 'desocupado', ativo BOOLEAN NOT NULL DEFAULT TRUE,
 CHECK (valor_diaria > 0 AND valor_mensal >= 0 AND capacidade > 0),
 CHECK (status IN ('ocupado','desocupado'))
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS funcionarios (
 id INT AUTO_INCREMENT PRIMARY KEY, nome VARCHAR(100) NOT NULL,
 cpf CHAR(11) NOT NULL UNIQUE, telefone VARCHAR(11) NOT NULL,
 cargo VARCHAR(60) NOT NULL, ativo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS usuarios (
 id INT AUTO_INCREMENT PRIMARY KEY, login VARCHAR(60) NOT NULL UNIQUE,
 senha_hash VARCHAR(255) NOT NULL, perfil VARCHAR(20) NOT NULL,
 ativo BOOLEAN NOT NULL DEFAULT TRUE, tentativas INT NOT NULL DEFAULT 0,
 bloqueado_ate DATETIME NULL, CHECK (perfil IN ('admin','recepcao'))
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS reservas (
 id INT AUTO_INCREMENT PRIMARY KEY, cliente_id INT NOT NULL, quarto_id INT NOT NULL,
 funcionario_id INT NULL, entrada DATE NOT NULL, saida DATE NOT NULL,
 diaria DECIMAL(10,2) NOT NULL, total DECIMAL(12,2) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'reservada',
 checkin_em DATETIME NULL, checkout_em DATETIME NULL,
 FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT,
 FOREIGN KEY (quarto_id) REFERENCES quartos(id) ON DELETE RESTRICT,
 FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE RESTRICT,
 INDEX disponibilidade (quarto_id,status,entrada,saida),
 CHECK (saida > entrada AND diaria > 0 AND total > 0),
 CHECK (status IN ('reservada','hospedada','finalizada','cancelada'))
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS pagamentos (
 id INT AUTO_INCREMENT PRIMARY KEY, reserva_id INT NOT NULL,
 valor DECIMAL(12,2) NOT NULL, forma VARCHAR(20) NOT NULL,
 status VARCHAR(10) NOT NULL, recebido_em DATETIME NULL,
 FOREIGN KEY (reserva_id) REFERENCES reservas(id) ON DELETE RESTRICT,
 CHECK (valor > 0), CHECK (status IN ('Pendente','Pago')),
 CHECK (forma IN ('Dinheiro','Cartao','PIX','Transferencia'))
) ENGINE=InnoDB;
