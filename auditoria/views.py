from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages


def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_logado'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def query(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def execute(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
    return True


@login_required
def auditoria(request):
    """Lista todos os registros de auditoria"""
    filtro_tabela = request.GET.get('tabela', '')
    filtro_operacao = request.GET.get('operacao', '')
    filtro_dias = request.GET.get('dias', '7')
    
    sql = """
        SELECT 
            ID_auditoria,
            Tabela_afetada,
            Operacao,
            ID_registro,
            Usuario_sistema,
            Data_hora,
            Dados_antigos,
            Dados_novos,
            Campos_alterados,
            Descricao
        FROM Auditoria
        WHERE 1=1
    """
    params = []
    
    if filtro_tabela:
        sql += " AND Tabela_afetada = %s"
        params.append(filtro_tabela)
    
    if filtro_operacao:
        sql += " AND Operacao = %s"
        params.append(filtro_operacao)
    
    if filtro_dias and filtro_dias.isdigit():
        sql += " AND Data_hora >= DATE_SUB(NOW(), INTERVAL %s DAY)"
        params.append(int(filtro_dias))
    
    sql += " ORDER BY Data_hora DESC LIMIT 100"
    
    dados = query(sql, params)
    tabelas = query("SELECT DISTINCT Tabela_afetada FROM Auditoria ORDER BY Tabela_afetada")
    
    context = {
        'dados': dados,
        'tabelas': tabelas,
        'filtro_tabela': filtro_tabela,
        'filtro_operacao': filtro_operacao,
        'filtro_dias': filtro_dias
    }
    
    return render(request, 'auditoria.html', context)


@login_required
def auditoria_detalhes(request, id):
    """Mostra detalhes de um registro de auditoria"""
    audit = query("SELECT * FROM Auditoria WHERE ID_auditoria = %s", [id])
    
    if not audit:
        messages.error(request, "Registro de auditoria não encontrado")
        return redirect('auditoria')
    
    return render(request, 'auditoria_detalhes.html', {'audit': audit[0]})


@login_required
def limpar_auditoria(request):
    """Limpa registros antigos de auditoria (mais de 90 dias)"""
    if request.method == 'POST':
        dias = request.POST.get('dias', '90')
        
        if not dias.isdigit():
            messages.error(request, "Número de dias inválido")
            return redirect('auditoria')
        
        result = query("""
            SELECT COUNT(*) as total 
            FROM Auditoria 
            WHERE Data_hora < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, [int(dias)])
        
        total = result[0]['total'] if result else 0
        
        execute("""
            DELETE FROM Auditoria 
            WHERE Data_hora < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, [int(dias)])
        
        messages.success(request, f"{total} registros de auditoria removidos (mais de {dias} dias)")
        return redirect('auditoria')
    
    return redirect('auditoria')
