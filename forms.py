from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

class CriarUsuarioForm(FlaskForm):
    username = StringField(
        'Nome de Usuário:',
        validators=[
            DataRequired(message="O nome de usuário é obrigatório."),
            Regexp(r'^[a-zA-Z0-9_]+$', message="Use apenas letras, números e underscore.")
        ]
    )
    nome_completo = StringField(
        'Nome Completo:',
        validators=[DataRequired(message="O nome completo é obrigatório.")]
    )
    email = StringField(
        'E-mail:',
        validators=[DataRequired(message="O e-mail é obrigatório."), Email(message="E-mail inválido.")]
    )
    tipo_permissao = SelectField(
        'Tipo de Permissão:',
        choices=[('', 'Selecione...'), ('colaborador', 'Colaborador'), ('admin', 'Administrador')],
        validators=[DataRequired(message="Selecione o tipo de permissão.")]
    )
    senha = PasswordField(
        'Senha:',
        validators=[DataRequired(message="A senha é obrigatória."), Length(min=6, message="Mínimo 6 caracteres.")]
    )
    confirmar_senha = PasswordField(
        'Confirmar Senha:',
        validators=[DataRequired(message="Confirme a senha."), EqualTo('senha', message="As senhas não coincidem.")]
    )
    submit = SubmitField('Criar Usuário')

class TrocarSenhaForm(FlaskForm):
    senha_atual = PasswordField('Senha Atual', validators=[DataRequired()])
    nova_senha = PasswordField('Nova Senha', validators=[DataRequired()])
    confirmar = PasswordField('Confirmar Nova Senha', validators=[
        DataRequired(),
        EqualTo('nova_senha', message='As senhas devem coincidir.')
    ])
    submit = SubmitField('Trocar Senha')