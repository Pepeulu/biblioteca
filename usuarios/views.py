from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.db.utils import IntegrityError
from .login_ultilitarios import autenticar_usuario, criar_usuario
from datetime import date


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
def usuarios(request):
    # usuario_id = request.session.get('usuario_logado')
    dados = query("SELECT * FROM Usuarios") #WHERE ID_usuario=%s", [usuario_id])
    return render(request, 'usuarios.html', {'dados': dados})


@login_required
def usuarios_edit(request, id):
    usuario_id = request.session.get('usuario_logado')

    if usuario_id != id:
        messages.error(request, "Você só pode editar seu próprio perfil.")
        return redirect('usuarios')

    if request.method == 'POST':
        nome = request.POST['nome']
        email = request.POST['email']
        telefone = request.POST['telefone']
        multa = request.POST['multa']

        execute("""
            UPDATE Usuarios 
            SET Nome_usuario=%s, Email=%s, Numero_telefone=%s, Multa_atual=%s
            WHERE ID_usuario=%s
        """, [nome, email, telefone, multa, id])

        messages.success(request, "Seus dados foram atualizados com sucesso!")
        return redirect('usuarios')

    usuario = query("SELECT * FROM Usuarios WHERE ID_usuario=%s", [id])[0]
    return render(request, 'usuarios_edit.html', {'usuario': usuario})

@login_required
def usuarios_delete(request, id):
    usuario_id = request.session.get('usuario_logado')

    if usuario_id != id:
        messages.error(request, "Você só pode excluir seu próprio perfil.")
        return redirect('usuarios')
    
    try:
        execute("DELETE FROM Usuarios WHERE ID_usuario=%s", [id])
    except (TypeError, ValueError, IntegrityError):
        messages.error(request, "não foi possivel realizar")
    return redirect('usuarios')

@login_required
def usuario_detalhes(request, id):
    request.session.flush()
    messages.info(request, "Você saiu da conta.")
    usuario = query("SELECT * FROM Usuarios WHERE ID_usuario=%s", [id])[0]
    return render(request, 'usuario_detalhes.html', {'usuario': usuario})

def register_view(request):
    if request.method == 'POST':
        nome = request.POST['nome']
        email = request.POST['email']
        telefone = request.POST['telefone']
        multa = request.POST.get('multa', 0)
        senha = request.POST['senha']
        confirmar = request.POST['confirmar']

        if senha != confirmar:
            messages.error(request, "As senhas não coincidem.")
            return render(request, 'register.html')

        data_criacao = date.today()

        criar_usuario(nome, email, telefone, data_criacao, multa, senha)
        messages.success(request, "Cadastro criado com sucesso! Faça login.")
        return redirect('login')

    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        senha = request.POST['senha']
        user = autenticar_usuario(email, senha)

        if user:
            request.session['usuario_logado'] = user[0]
            request.session['nome_usuario'] = user[1]
            messages.success(request, f"Bem-vindo, {user[1]}!")
            return redirect('index')
        else:
            messages.error(request, "Email ou senha incorretos.")
            return render(request, 'login.html')

    return render(request, 'login.html')

@login_required
def logout_view(request):
    request.session.flush()
    messages.info(request, "Você saiu da conta.")
    return redirect('login')