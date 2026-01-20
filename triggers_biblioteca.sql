USE db_atividade17;

CREATE TABLE IF NOT EXISTS Auditoria (
    ID_auditoria INT AUTO_INCREMENT PRIMARY KEY,
    Tabela_afetada VARCHAR(100) NOT NULL,
    Operacao ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    ID_registro INT,
    Usuario_sistema VARCHAR(100),
    Data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Dados_antigos TEXT,
    Dados_novos TEXT,
    Campos_alterados TEXT,
    Descricao TEXT
) ENGINE=InnoDB;


DELIMITER $$
DROP TRIGGER IF EXISTS livros_validar_insert$$
CREATE TRIGGER livros_validar_insert
BEFORE INSERT ON Livros
FOR EACH ROW
BEGIN
    -- Validar ISBN com 13 caracteres
    IF LENGTH(TRIM(NEW.ISBN)) != 13 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'ISBN deve conter exatamente 13 caracteres';
    END IF;
    
    -- Validar ISBN duplicado
    IF EXISTS (SELECT 1 FROM Livros WHERE ISBN = NEW.ISBN) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'ISBN já cadastrado no sistema';
    END IF;
    
    -- Validar quantidade disponível não negativa
    IF NEW.Quantidade_disponivel < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Quantidade disponível não pode ser negativa';
    END IF;
END$$

DROP TRIGGER IF EXISTS emprestimos_validar_insert$$
CREATE TRIGGER emprestimos_validar_insert
BEFORE INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    DECLARE qtd_disponivel INT;
    DECLARE emprestimos_ativos INT;
    DECLARE multa_usuario DECIMAL(10,2);
    
    -- Verificar disponibilidade do livro
    SELECT Quantidade_disponivel INTO qtd_disponivel
    FROM Livros WHERE ID_livro = NEW.Livro_id;
    
    IF qtd_disponivel <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Livro não disponível para empréstimo';
    END IF;
    
    -- Validar limite de empréstimos por usuário (máximo 5 ativos)
    SELECT COUNT(*) INTO emprestimos_ativos
    FROM Emprestimos
    WHERE Usuario_id = NEW.Usuario_id 
    AND Status_emprestimo = 'pendente';
    
    IF emprestimos_ativos >= 5 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário já possui 5 empréstimos ativos (limite máximo)';
    END IF;
    
    -- Verificar se usuário tem multas pendentes acima de R$ 50
    SELECT COALESCE(Multa_atual, 0) INTO multa_usuario
    FROM Usuarios WHERE ID_usuario = NEW.Usuario_id;
    
    IF multa_usuario > 50.00 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Usuário possui multa acima de R$ 50.00. Não pode realizar novos empréstimos';
    END IF;
END$$


DROP TRIGGER IF EXISTS usuarios_validar_insert$$
CREATE TRIGGER usuarios_validar_insert
BEFORE INSERT ON Usuarios
FOR EACH ROW
BEGIN
    -- Validar email único
    IF NEW.Email IS NOT NULL AND EXISTS (SELECT 1 FROM Usuarios WHERE Email = NEW.Email) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Email já cadastrado no sistema';
    END IF;
    
    -- Validar formato de email básico
    IF NEW.Email IS NOT NULL AND NEW.Email NOT LIKE '%@%.%' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Formato de email inválido';
    END IF;
    
    -- Validar multa não pode ser negativa
    IF NEW.Multa_atual < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Multa não pode ser negativa';
    END IF;
END$$

DROP TRIGGER IF EXISTS autores_validar_insert$$
CREATE TRIGGER autores_validar_insert
BEFORE INSERT ON Autores
FOR EACH ROW
BEGIN
    -- Validar data de nascimento não pode ser futura
    IF NEW.Data_nascimento IS NOT NULL AND NEW.Data_nascimento > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Data de nascimento não pode ser no futuro';
    END IF;
    
    -- Validar idade mínima (autor deve ter pelo menos 10 anos)
    IF NEW.Data_nascimento IS NOT NULL AND TIMESTAMPDIFF(YEAR, NEW.Data_nascimento, CURDATE()) < 10 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Autor deve ter pelo menos 10 anos de idade';
    END IF;
END$$

DROP TRIGGER IF EXISTS generos_validar_insert$$
CREATE TRIGGER generos_validar_insert
BEFORE INSERT ON Generos
FOR EACH ROW
BEGIN
    -- Validar nome não vazio
    IF TRIM(NEW.Nome_genero) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Nome do gênero não pode ser vazio';
    END IF;
    
    -- Impedir gêneros duplicados
    IF EXISTS (SELECT 1 FROM Generos WHERE LOWER(Nome_genero) = LOWER(NEW.Nome_genero)) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Este gênero já está cadastrado';
    END IF;
END$$

DELIMITER ;



DELIMITER $$


DROP TRIGGER IF EXISTS livros_audit_insert$$
CREATE TRIGGER livros_audit_insert
AFTER INSERT ON Livros
FOR EACH ROW
BEGIN
    INSERT INTO Auditoria (
        Tabela_afetada,
        Operacao,
        ID_registro,
        Usuario_sistema,
        Dados_novos,
        Descricao
    ) VALUES (
        'Livros',
        'INSERT',
        NEW.ID_livro,
        USER(),
        CONCAT('Título: ', NEW.Titulo, ', ISBN: ', NEW.ISBN, ', Quantidade: ', NEW.Quantidade_disponivel),
        CONCAT('Novo livro cadastrado: ', NEW.Titulo)
    );
END$$


DROP TRIGGER IF EXISTS livros_audit_update$$
CREATE TRIGGER livros_audit_update
AFTER UPDATE ON Livros
FOR EACH ROW
BEGIN
    DECLARE campos_alterados TEXT DEFAULT '';
    
    -- Identificar campos alterados
    IF OLD.Titulo != NEW.Titulo THEN
        SET campos_alterados = CONCAT(campos_alterados, 'Título: ', OLD.Titulo, ' -> ', NEW.Titulo, '; ');
    END IF;
    
    IF OLD.Quantidade_disponivel != NEW.Quantidade_disponivel THEN
        SET campos_alterados = CONCAT(campos_alterados, 'Quantidade: ', OLD.Quantidade_disponivel, ' -> ', NEW.Quantidade_disponivel, '; ');
    END IF;
    
    INSERT INTO Auditoria (
        Tabela_afetada,
        Operacao,
        ID_registro,
        Usuario_sistema,
        Dados_antigos,
        Dados_novos,
        Campos_alterados,
        Descricao
    ) VALUES (
        'Livros',
        'UPDATE',
        NEW.ID_livro,
        USER(),
        CONCAT('Título: ', OLD.Titulo, ', Qtd: ', OLD.Quantidade_disponivel),
        CONCAT('Título: ', NEW.Titulo, ', Qtd: ', NEW.Quantidade_disponivel),
        campos_alterados,
        CONCAT('Livro atualizado: ', NEW.Titulo)
    );
END$$


DROP TRIGGER IF EXISTS emprestimos_audit_insert$$
CREATE TRIGGER emprestimos_audit_insert
AFTER INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    INSERT INTO Auditoria (
        Tabela_afetada,
        Operacao,
        ID_registro,
        Usuario_sistema,
        Dados_novos,
        Descricao
    ) VALUES (
        'Emprestimos',
        'INSERT',
        NEW.ID_emprestimo,
        USER(),
        CONCAT('Usuario_id: ', NEW.Usuario_id, ', Livro_id: ', NEW.Livro_id, ', Status: ', NEW.Status_emprestimo),
        CONCAT('Novo empréstimo registrado - ID: ', NEW.ID_emprestimo)
    );
END$$


DROP TRIGGER IF EXISTS emprestimos_audit_update$$
CREATE TRIGGER emprestimos_audit_update
AFTER UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    DECLARE campos_alterados TEXT DEFAULT '';
    
    IF OLD.Status_emprestimo != NEW.Status_emprestimo THEN
        SET campos_alterados = CONCAT(campos_alterados, 'Status: ', OLD.Status_emprestimo, ' -> ', NEW.Status_emprestimo, '; ');
    END IF;
    
    IF COALESCE(OLD.Data_devolucao_real, '1900-01-01') != COALESCE(NEW.Data_devolucao_real, '1900-01-01') THEN
        SET campos_alterados = CONCAT(campos_alterados, 'Data_devolucao_real: ', COALESCE(OLD.Data_devolucao_real, 'NULL'), ' -> ', COALESCE(NEW.Data_devolucao_real, 'NULL'), '; ');
    END IF;
    
    INSERT INTO Auditoria (
        Tabela_afetada,
        Operacao,
        ID_registro,
        Usuario_sistema,
        Dados_antigos,
        Dados_novos,
        Campos_alterados,
        Descricao
    ) VALUES (
        'Emprestimos',
        'UPDATE',
        NEW.ID_emprestimo,
        USER(),
        CONCAT('Status: ', OLD.Status_emprestimo),
        CONCAT('Status: ', NEW.Status_emprestimo),
        campos_alterados,
        CONCAT('Empréstimo atualizado - ID: ', NEW.ID_emprestimo)
    );
END$$


DROP TRIGGER IF EXISTS usuarios_audit_update$$
CREATE TRIGGER usuarios_audit_update
AFTER UPDATE ON Usuarios
FOR EACH ROW
BEGIN
    DECLARE campos_alterados TEXT DEFAULT '';
    
    IF OLD.Multa_atual != NEW.Multa_atual THEN
        SET campos_alterados = CONCAT(campos_alterados, 'Multa: R$ ', OLD.Multa_atual, ' -> R$ ', NEW.Multa_atual, '; ');
    END IF;
    
    IF COALESCE(OLD.Email, '') != COALESCE(NEW.Email, '') THEN
        SET campos_alterados = CONCAT(campos_alterados, 'Email: ', COALESCE(OLD.Email, 'NULL'), ' -> ', COALESCE(NEW.Email, 'NULL'), '; ');
    END IF;
    
    INSERT INTO Auditoria (
        Tabela_afetada,
        Operacao,
        ID_registro,
        Usuario_sistema,
        Dados_antigos,
        Dados_novos,
        Campos_alterados,
        Descricao
    ) VALUES (
        'Usuarios',
        'UPDATE',
        NEW.ID_usuario,
        USER(),
        CONCAT('Nome: ', OLD.Nome_usuario, ', Multa: R$ ', OLD.Multa_atual),
        CONCAT('Nome: ', NEW.Nome_usuario, ', Multa: R$ ', NEW.Multa_atual),
        campos_alterados,
        CONCAT('Usuário atualizado: ', NEW.Nome_usuario)
    );
END$$

DELIMITER ;


DELIMITER $$



DROP TRIGGER IF EXISTS emprestimos_diminuir_estoque$$
CREATE TRIGGER emprestimos_diminuir_estoque
AFTER INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    UPDATE Livros
    SET Quantidade_disponivel = Quantidade_disponivel - 1
    WHERE ID_livro = NEW.Livro_id;
END$$


DROP TRIGGER IF EXISTS emprestimos_aumentar_estoque$$
CREATE TRIGGER emprestimos_aumentar_estoque
AFTER UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    -- Se mudou de não-devolvido para devolvido
    IF OLD.Status_emprestimo != 'devolvido' AND NEW.Status_emprestimo = 'devolvido' THEN
        UPDATE Livros
        SET Quantidade_disponivel = Quantidade_disponivel + 1
        WHERE ID_livro = NEW.Livro_id;
    END IF;
    
    -- Se mudou de devolvido para não-devolvido (raro, mas possível)
    IF OLD.Status_emprestimo = 'devolvido' AND NEW.Status_emprestimo != 'devolvido' THEN
        UPDATE Livros
        SET Quantidade_disponivel = Quantidade_disponivel - 1
        WHERE ID_livro = NEW.Livro_id;
    END IF;
END$$


DROP TRIGGER IF EXISTS emprestimos_restaurar_estoque$$
CREATE TRIGGER emprestimos_restaurar_estoque
AFTER DELETE ON Emprestimos
FOR EACH ROW
BEGIN
    -- Só restaura se o empréstimo não estava devolvido
    IF OLD.Status_emprestimo != 'devolvido' THEN
        UPDATE Livros
        SET Quantidade_disponivel = Quantidade_disponivel + 1
        WHERE ID_livro = OLD.Livro_id;
    END IF;
END$$


DROP TRIGGER IF EXISTS emprestimos_calcular_multa$$
CREATE TRIGGER emprestimos_calcular_multa
AFTER UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    DECLARE dias_atraso INT;
    DECLARE multa_calculada DECIMAL(10,2);
    
    -- Se foi devolvido agora (mudou status para devolvido)
    IF OLD.Status_emprestimo != 'devolvido' AND NEW.Status_emprestimo = 'devolvido' THEN
        -- Calcula dias de atraso
        SET dias_atraso = DATEDIFF(
            COALESCE(NEW.Data_devolucao_real, CURDATE()), 
            NEW.Data_devolucao_prevista
        );
        
        -- Se atrasou, calcula multa (R$ 2,00 por dia de atraso)
        IF dias_atraso > 0 THEN
            SET multa_calculada = dias_atraso * 2.00;
            
            -- Adiciona multa ao usuário
            UPDATE Usuarios
            SET Multa_atual = Multa_atual + multa_calculada
            WHERE ID_usuario = NEW.Usuario_id;
        END IF;
    END IF;
END$$


DROP TRIGGER IF EXISTS emprestimos_marcar_atrasados$$
CREATE TRIGGER emprestimos_marcar_atrasados
BEFORE UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    -- Se ainda está pendente e passou da data prevista, marca como atrasado
    IF NEW.Status_emprestimo = 'pendente' 
       AND NEW.Data_devolucao_prevista < CURDATE() 
       AND NEW.Data_devolucao_real IS NULL THEN
        SET NEW.Status_emprestimo = 'atrasado';
    END IF;
END$$

DELIMITER ;



DELIMITER $$


DROP TRIGGER IF EXISTS usuarios_gerar_valores$$
CREATE TRIGGER usuarios_gerar_valores
BEFORE INSERT ON Usuarios
FOR EACH ROW
BEGIN
    -- Se data de inscrição não foi fornecida, usa data atual
    IF NEW.Data_inscricao IS NULL THEN
        SET NEW.Data_inscricao = CURDATE();
    END IF;
    
    -- Inicializa multa como zero se não foi fornecida
    IF NEW.Multa_atual IS NULL THEN
        SET NEW.Multa_atual = 0.00;
    END IF;
END$$


DROP TRIGGER IF EXISTS emprestimos_gerar_valores$$
CREATE TRIGGER emprestimos_gerar_valores
BEFORE INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    -- Se data de empréstimo não foi fornecida, usa data atual
    IF NEW.Data_emprestimo IS NULL THEN
        SET NEW.Data_emprestimo = CURDATE();
    END IF;
    
    -- Se data de devolução prevista não foi fornecida, define como 14 dias após empréstimo
    IF NEW.Data_devolucao_prevista IS NULL THEN
        SET NEW.Data_devolucao_prevista = DATE_ADD(NEW.Data_emprestimo, INTERVAL 14 DAY);
    END IF;
    
    -- Define status inicial como 'pendente' se não foi fornecido
    IF NEW.Status_emprestimo IS NULL THEN
        SET NEW.Status_emprestimo = 'pendente';
    END IF;
END$$


DROP TRIGGER IF EXISTS emprestimos_gerar_data_devolucao$$
CREATE TRIGGER emprestimos_gerar_data_devolucao
BEFORE UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    -- Se mudou para devolvido e não tem data de devolução real, gera automaticamente
    IF NEW.Status_emprestimo = 'devolvido' 
       AND OLD.Status_emprestimo != 'devolvido' 
       AND NEW.Data_devolucao_real IS NULL THEN
        SET NEW.Data_devolucao_real = CURDATE();
    END IF;
END$$

DROP TRIGGER IF EXISTS livros_gerar_valores$$
CREATE TRIGGER livros_gerar_valores
BEFORE INSERT ON Livros
FOR EACH ROW
BEGIN
    -- Se ano não foi fornecido, usa ano atual
    IF NEW.Ano_publicacao IS NULL THEN
        SET NEW.Ano_publicacao = YEAR(CURDATE());
    END IF;
    
    -- Se quantidade não foi fornecida, inicia com 1
    IF NEW.Quantidade_disponivel IS NULL THEN
        SET NEW.Quantidade_disponivel = 1;
    END IF;
END$$


DROP TRIGGER IF EXISTS livros_normalizar_dados$$
CREATE TRIGGER livros_normalizar_dados
BEFORE INSERT ON Livros
FOR EACH ROW
BEGIN
    SET NEW.Titulo = TRIM(NEW.Titulo);
    SET NEW.ISBN = TRIM(NEW.ISBN);
    SET NEW.Resumo = TRIM(COALESCE(NEW.Resumo, ''));
END$$

SET GLOBAL event_scheduler = ON;

DELIMITER $$

DROP EVENT IF EXISTS atualizar_emprestimos_atrasados$$
CREATE EVENT atualizar_emprestimos_atrasados
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_DATE + INTERVAL 1 DAY
DO
BEGIN
    -- Atualiza empréstimos pendentes que passaram da data prevista
    UPDATE Emprestimos
    SET Status_emprestimo = 'atrasado'
    WHERE Status_emprestimo = 'pendente'
    AND Data_devolucao_prevista < CURDATE()
    AND Data_devolucao_real IS NULL;
END$$