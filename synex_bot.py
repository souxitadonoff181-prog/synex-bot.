import discord
from discord import app_commands, ui
from discord.ui import View, Button, Select
import json
import os
import qrcode
from io import BytesIO
from datetime import datetime
import uuid
import random

# ==============================================
# SYNEX — CONFIGURAÇÕES
# ==============================================
NOME_SISTEMA = "Synex"
import os

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [int(os.getenv("ADMIN_ID"))]

BANCOS_COMPATIVEIS = [
    "Nubank", "Itaú", "Bradesco", "Banco do Brasil", "Santander",
    "Caixa", "Banco Inter", "C6 Bank", "PicPay", "Mercado Pago",
    "PagBank", "Neon", "Next", "Sicredi", "Sicoob", "Banrisul"
]

ARQUIVOS = {
    "config": "synex_config.json",
    "produtos": "synex_produtos.json",
    "tickets": "synex_tickets.json",
    "avaliacoes": "synex_avaliacoes.json",
    "sorteios": "synex_sorteios.json",
    "bemvindo": "synex_bemvindo.json",
    "logs": "synex_logs.json"
}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ==============================================
# FUNÇÕES
# ==============================================
def carregar():
    dados = {}
    for nome, caminho in ARQUIVOS.items():
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                dados[nome] = json.load(f)
        else:
            dados[nome] = {}
    return dados

def salvar(nome, conteudo):
    with open(ARQUIVOS[nome], "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=4)

CONFIG, PRODUTOS, TICKETS, AVALIACOES, SORTEIOS, BEMVINDO, LOGS = carregar().values()

# ==============================================
# GERAR PIX
# ==============================================
def gerar_qr_pix(chave, nome, valor):
    payload = (
        f"00020126{14+2+len(chave):02d}0014br.gov.bcb.pix01{len(chave):02d}{chave}"
        f"5204000053039865802BR59{len(nome):02d}{nome}6006BRASIL62070503***6304"
    )
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf, payload

# ==============================================
# ENTREGAR PRODUTO NO PRIVADO
# ==============================================
async def entregar_produto_dm(usuario, produto):
    tem_link = "link" in produto and produto["link"]
    tem_key = "chaves" in produto and len(produto["chaves"]) > 0
    
    if not tem_link and not tem_key:
        return False
    
    emb = discord.Embed(
        title="✅ SYNEX — COMPRA APROVADA!",
        description=f"Olá {usuario.mention}, sua compra foi confirmada!\n\n📦 **Produto:** {produto['nome']}",
        color=0x00ff88
    )
    
    if tem_link:
        emb.add_field(name="🔗 Download", value=produto["link"], inline=False)
    if tem_key:
        chave = produto["chaves"].pop(0)
        emb.add_field(name="🔑 Sua Key", value=f"`{chave}`", inline=False)
        salvar("produtos", PRODUTOS)
    
    emb.add_field(name="💬 Suporte", value="Abra um ticket se precisar de ajuda!", inline=False)
    emb.set_footer(text=f"Obrigado por confiar na {NOME_SISTEMA}! 💙")
    
    try:
        await usuario.send(embed=emb)
        return True
    except:
        return False

# ==============================================
# AVALIAÇÃO
# ==============================================
class AvaliarView(View):
    def __init__(self, atendente_id):
        super().__init__(timeout=None)
        self.atendente_id = atendente_id

    @ui.button(label="⭐", style=discord.ButtonStyle.red)
    async def b1(self, i, b): await self.nota(i, 1)
    @ui.button(label="⭐⭐", style=discord.ButtonStyle.Red)
    async def b2(self, i, b): await self.nota(i, 2)
    @ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.Blurple)
    async def b3(self, i, b): await self.nota(i, 3)
    @ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.Green)
    async def b4(self, i, b): await self.nota(i, 4)
    @ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.Green)
    async def b5(self, i, b): await self.nota(i, 5)

    async def nota(self, inter, valor):
        AVALIACOES[str(self.atendente_id)] = AVALIACOES.get(str(self.atendente_id), []) + [valor]
        salvar("avaliacoes", AVALIACOES)
        atendente = client.get_user(self.atendente_id)
        if atendente:
            try:
                media = sum(AVALIACOES[str(self.atendente_id)]) / len(AVALIACOES[str(self.atendente_id)])
                await atendente.send(
                    f"⭐ **SYNEX — NOVA AVALIAÇÃO!**\n\n"
                    f"De: {inter.user.mention}\nNota: {'⭐'*valor} ({valor}/5)\nMédia: {media:.1f}/5"
                )
            except: pass
        await inter.response.send_message(f"✅ Obrigado! {'⭐'*valor}", ephemeral=True)

# ==============================================
# CONFIGURAÇÃO
# ==============================================
@tree.command(name="synex_config", description="Configurar Synex")
@app_commands.checks.has_permissions(administrator=True)
async def config(inter, chave_pix:str=None, titular:str=None, banco:str=None, 
                  categoria_tickets:str=None, cargo_compra:str=None, entrega_automatica:bool=None):
    if banco and banco not in BANCOS_COMPATIVEIS:
        return await inter.response.send_message(
            f"⚠️ Verifique o banco! Compatíveis: {', '.join(BANCOS_COMPATIVEIS[:8])}...", ephemeral=True
        )
    if chave_pix: CONFIG["chave_pix"] = chave_pix
    if titular: CONFIG["titular"] = titular
    if banco: CONFIG["banco"] = banco
    if categoria_tickets: CONFIG["cat_tickets"] = int(categoria_tickets)
    if cargo_compra: CONFIG["cargo_compra"] = int(cargo_compra)
    if entrega_automatica is not None: CONFIG["entrega_auto"] = entrega_automatica
    salvar("config", CONFIG)
    await inter.response.send_message("✅ Configurações salvas!", ephemeral=True)

# ==============================================
# CADASTRAR PRODUTO
# ==============================================
@tree.command(name="synex_produto_adicionar", description="Cadastrar produto")
@app_commands.checks.has_permissions(administrator=True)
async def prod_add(inter, id:str, nome:str, preco:float, link:str="", chave:str="", descricao:str="", imagem:str=""):
    if not link and not chave:
        return await inter.response.send_message("❌ Precisa de link OU key!", ephemeral=True)
    PRODUTOS[id] = {
        "nome": nome, "preco": preco, "link": link,
        "chaves": [chave] if chave else [],
        "descricao": descricao, "imagem": imagem
    }
    salvar("produtos", PRODUTOS)
    await inter.response.send_message(f"✅ Produto `{nome}` cadastrado!", ephemeral=True)

@tree.command(name="synex_key_adicionar", description="Adicionar key")
@app_commands.checks.has_permissions(administrator=True)
async def key_add(inter, produto_id:str, chave:str):
    if produto_id not in PRODUTOS:
        return await inter.response.send_message("❌ Produto não existe!", ephemeral=True)
    PRODUTOS[produto_id]["chaves"].append(chave)
    salvar("produtos", PRODUTOS)
    await inter.response.send_message(f"✅ Key adicionada! Total: {len(PRODUTOS[produto_id]['chaves'])}", ephemeral=True)

# ==============================================
# CONFIRMAR COMPRA → ENTREGA NO PRIVADO
# ==============================================
@tree.command(name="synex_confirmar", description="Confirmar compra")
@app_commands.checks.has_permissions(administrator=True)
async def confirmar(inter, usuario:discord.User, produto_id:str):
    prod = PRODUTOS.get(produto_id)
    if not prod:
        return await inter.response.send_message("❌ Produto não existe!", ephemeral=True)
    
    if CONFIG.get("cargo_compra"):
        cargo = inter.guild.get_role(CONFIG["cargo_compra"])
        if cargo: await usuario.add_roles(cargo)
    
    entrega_ok = False
    if CONFIG.get("entrega_auto", True):
        entrega_ok = await entregar_produto_dm(usuario, prod)
    
    await inter.response.send_message(
        f"✅ {usuario.mention} → {'entregue no privado' if entrega_ok else 'DM fechada, avise manualmente'}!",
        ephemeral=True
    )

# ==============================================
# COMPRAR → GERAR PIX
# ==============================================
@tree.command(name="synex_comprar", description="Iniciar compra")
async def comprar(inter, produto_id:str):
    prod = PRODUTOS.get(produto_id)
    if not prod:
        return await inter.response.send_message("❌ Produto não encontrado!", ephemeral=True)
    
    class Pag(View):
        @ui.button(label="💳 PIX", style=discord.ButtonStyle.Green)
        async def pix_btn(self, i, b):
            chave = CONFIG.get("chave_pix")
            if not chave:
                return await i.response.send_message("❌ Configure PIX com /synex_config", ephemeral=True)
            qr, cod = gerar_qr_pix(chave, CONFIG.get("titular", NOME_SISTEMA), prod["preco"])
            emb = discord.Embed(
                title="💵 SYNEX — PAGAMENTO",
                description=f"Banco: {CONFIG.get('banco', 'Não definido')}\nProduto: {prod['nome']}\nValor: R$ {prod['preco']:.2f}",
                color=0x00cc00
            )
            emb.set_image(url="attachment://qr.png")
            await i.response.send_message(embed=emb, file=discord.File(qr, "qr.png"), ephemeral=True)
    
    emb = discord.Embed(title="🛒 SYNEX — COMPRAR", description=f"{prod['nome']}\nR$ {prod['preco']:.2f}", color=0xffaa00)
    await inter.response.send_message(embed=emb, view=Pag(), ephemeral=True)

# ==============================================
# PAINEL DE VENDAS
# ==============================================
@tree.command(name="synex_painel_vendas", description="Enviar painel de vendas")
@app_commands.checks.has_permissions(administrator=True)
async def painel_vendas(inter, produto_id:str):
    p = PRODUTOS.get(produto_id)
    if not p:
        return await inter.response.send_message("❌ Produto não existe!", ephemeral=True)
    
    class Painel(View):
        @ui.button(label="🛒 Comprar Agora", style=discord.ButtonStyle.Green)
        async def comprar_btn(self, i, b):
            await comprar.callback(i, produto_id)
    
    emb = discord.Embed(title=f"🎁 {p['nome']}", description=p["descricao"], color=0x00ccff)
    if p["imagem"]: emb.set_image(url=p["imagem"])
    emb.set_footer(text=f"Synex — ID: {produto_id}")
    await inter.channel.send(embed=emb, view=Painel())
    await inter.response.send_message("✅ Painel enviado!", ephemeral=True)

# ==============================================
# TICKETS
# ==============================================
@tree.command(name="synex_painel_atendimento", description="Painel de suporte")
@app_commands.checks.has_permissions(administrator=True)
async def painel_ticket(inter):
    class Ticket(View):
        @ui.select(placeholder="Selecione...", options=[
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"),
            discord.SelectOption(label="Denúncia", value="denuncia", emoji="⚠️"),
            discord.SelectOption(label="Parceria", value="parceria", emoji="🤝")
        ])
        async def sel(self, i, s):
            cat = client.get_channel(CONFIG.get("cat_tickets"))
            if not cat:
                return await i.response.send_message("❌ Configure categoria!", ephemeral=True)
            canal = await cat.create_text_channel(f"{s.values[0]}-{i.user.name}")
            await canal.set_permissions(i.user, view_messages=True, send_messages=True)
            await canal.set_permissions(i.guild.default_role, send_messages=False)
            TICKETS[str(canal.id)] = {"user": i.user.id, "assumido": None}
            salvar("tickets", TICKETS)
            try: await i.user.send(f"✅ Ticket aberto: {canal.mention}")
            except: pass
            emb = discord.Embed(title=f"🎫 Ticket — {s.values[0].title()}", 
                                description=f"Aberto por {i.user.mention}\nAssumido: Ninguém", color=0x00ccff)
            await canal.send(embed=emb)
            await i.response.send_message(f"✅ {canal.mention}", ephemeral=True)
    
    emb = discord.Embed(title="📞 SYNEX — ATENDIMENTO", color=0x00ccff)
    await inter.channel.send(embed=emb, view=Ticket())
    await inter.response.send_message("✅ Painel enviado!", ephemeral=True)

@tree.command(name="synex_assumir", description="Assumir ticket")
@app_commands.checks.has_permissions(manage_channels=True)
async def assumir(inter):
    t = TICKETS.get(str(inter.channel.id))
    if not t or t["assumido"]:
        return await inter.response.send_message("❌ Já assumido!", ephemeral=True)
    t["assumido"] = inter.user.id
    salvar("tickets", TICKETS)
    try:
        u = client.get_user(t["user"])
        if u: await u.send(f"🔔 Seu ticket foi assumido por {inter.user.mention}")
    except: pass
    await inter.response.send_message(f"✅ Assumido por {inter.user.mention}")

@tree.command(name="synex_fechar", description="Fechar ticket")
@app_commands.checks.has_permissions(manage_channels=True)
async def fechar(inter):
    t = TICKETS.get(str(inter.channel.id))
    if not t:
        return await inter.response.send_message("❌ Não é ticket!", ephemeral=True)
    
    atendente = t.get("assumido") or inter.user.id
    try:
        u = client.get_user(t["user"])
        if u:
            emb = discord.Embed(
                title="❌ TICKET FECHADO",
                description=f"Fechado por {inter.user.mention}",
                color=0xff4444
            )
            await u.send(embed=emb)
    except:
        pass
    
    # Aqui continua o resto do código de fechar...
    await inter.channel.delete()
