#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMULADOR DE TRANSMISSÃO — TEXTO PURO -> ASCII / MODBUS RTU / MODBUS ASCII CELSO RENE DOS SANTOS 
================================================================================================
Duas janelas gráficas (Tkinter):

  JANELA 1 — "Transmissor": onde você digita a mensagem em texto puro
             (letras, números, caracteres), como se fosse enviar para um
             CLP ou para um ponto de rede.

  JANELA 2 — "Receptor": mostra, em tempo real, como essa mensagem chega
             de fato à máquina — caractere a caractere convertido pela
             tabela ASCII (decimal / hex / binário), e a trama completa
             como seria transmitida no fio, em 3 formatos possíveis:

               1) ASCII puro       -> só os bytes da mensagem, em hex
               2) Modbus RTU       -> binário puro + CRC16 (padrão RTU)
               3) Modbus ASCII     -> cada byte vira 2 caracteres hex,
                                      com ':' no início, LRC e CRLF no fim
                                      (é o outro modo de transmissão do
                                      protocolo Modbus, por isso chamado
                                      "ASCII" — não confundir com o item 1)

Não precisa de bibliotecas externas — só a biblioteca padrão do Python.
No Linux, se tkinter não estiver instalado: sudo apt install python3-tk
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime


# --------------------------------------------------------------------------- #
# CÁLCULOS DE CHECKSUM (iguais aos usados de fato no protocolo Modbus)
# --------------------------------------------------------------------------- #
def calcular_lrc(bytes_dados):
    """LRC usado no Modbus ASCII: complemento de dois da soma dos bytes."""
    soma = sum(bytes_dados) & 0xFF
    return ((0xFF - soma) + 1) & 0xFF


def calcular_crc16_modbus(bytes_dados):
    """CRC16 usado no Modbus RTU (polinômio 0xA001). Retorna (byte_baixo, byte_alto)."""
    crc = 0xFFFF
    for b in bytes_dados:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFF, (crc >> 8) & 0xFF


# --------------------------------------------------------------------------- #
# APLICAÇÃO
# --------------------------------------------------------------------------- #
class SimuladorTransmissao:

    ENDERECO_SIMULADO = 0x01   # endereço de escravo fictício, só para exibição
    FUNCAO_SIMULADA = 0x41     # código de função fictício ("mensagem de texto")

    def __init__(self):
        self.janela1 = tk.Tk()
        self.janela1.title("Janela 1 — Transmissor (texto puro)")
        self.janela1.geometry("480x400")
        self.janela1.resizable(False, False)

        self.janela2 = tk.Toplevel(self.janela1)
        self.janela2.title("Janela 2 — Receptor (conversão ASCII / RTU)")
        self.janela2.geometry("680x560")

        # posiciona as duas janelas lado a lado
        self.janela1.geometry("+80+80")
        self.janela2.geometry("+580+80")

        self._montar_janela1()
        self._montar_janela2()

        self.janela1.protocol("WM_DELETE_WINDOW", self._fechar_tudo)
        self.janela2.protocol("WM_DELETE_WINDOW", self._fechar_tudo)

    # ------------------------------------------------------------- UI 1 ---
    def _montar_janela1(self):
        frame = ttk.Frame(self.janela1, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Mensagem (texto, números, caracteres):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.texto_var = tk.StringVar()
        self.entrada = ttk.Entry(frame, textvariable=self.texto_var, font=("Consolas", 13))
        self.entrada.pack(fill="x", pady=8)
        self.entrada.bind("<KeyRelease>", lambda e: self._atualizar())
        self.entrada.focus()

        self.lbl_contagem = ttk.Label(frame, text="0 caractere(s)", foreground="grey")
        self.lbl_contagem.pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=12)

        ttk.Label(frame, text="Formato de transmissão simulado:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.formato_var = tk.StringVar(value="ascii_puro")
        opcoes = [
            ("ASCII puro (byte a byte, sem protocolo)", "ascii_puro"),
            ("Modbus RTU  (binário + CRC16)", "rtu"),
            ("Modbus ASCII (hex em texto + LRC + CRLF)", "modbus_ascii"),
        ]
        for texto, valor in opcoes:
            ttk.Radiobutton(frame, text=texto, variable=self.formato_var, value=valor,
                            command=self._atualizar).pack(anchor="w", pady=2)

        ttk.Button(frame, text="Enviar mensagem  →",
                   command=self._enviar).pack(pady=16, fill="x")

        ttk.Label(frame, text="A conversão aparece em tempo real na Janela 2,\n"
                              "mesmo antes de clicar em Enviar.",
                  foreground="grey", justify="left").pack(anchor="w")

    # ------------------------------------------------------------- UI 2 ---
    def _montar_janela2(self):
        frame = ttk.Frame(self.janela2, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Tabela de conversão: caractere → ASCII",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        colunas = ("char", "dec", "hex", "bin")
        titulos = ("Caractere", "Decimal", "Hex", "Binário (8 bits)")
        larguras = (90, 80, 80, 150)
        self.tabela = ttk.Treeview(frame, columns=colunas, show="headings", height=8)
        for c, t, w in zip(colunas, titulos, larguras):
            self.tabela.heading(c, text=t)
            self.tabela.column(c, width=w, anchor="center")
        self.tabela.pack(fill="x", pady=6)

        ttk.Label(frame, text="Trama como seria enviada à máquina receptora (CLP / ponto de rede):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 2))
        self.trama_txt = scrolledtext.ScrolledText(frame, height=9, font=("Consolas", 10), wrap="word")
        self.trama_txt.pack(fill="both", expand=True)

        ttk.Label(frame, text="Histórico de mensagens enviadas:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 2))
        self.historico = scrolledtext.ScrolledText(frame, height=6, state="disabled",
                                                     font=("Consolas", 9))
        self.historico.pack(fill="both", expand=True)

    # ---------------------------------------------------------- lógica ---
    def _atualizar(self):
        texto = self.texto_var.get()
        self.lbl_contagem.config(text=f"{len(texto)} caractere(s)")

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        # converte para bytes ASCII; caracteres fora da tabela (acentos etc.)
        # são substituídos por '?' (0x3F) e avisados na trama
        bytes_msg = texto.encode("ascii", errors="replace")

        for ch, b in zip(texto, bytes_msg):
            exibicao = "(espaço)" if ch == " " else ch
            self.tabela.insert("", "end", values=(exibicao, b, f"0x{b:02X}", format(b, "08b")))

        self.trama_txt.delete("1.0", "end")
        if not texto:
            self.trama_txt.insert("end", "Digite algo na Janela 1 para ver a conversão aqui.")
            return

        if any(ord(c) > 127 for c in texto):
            self.trama_txt.insert(
                "end",
                "⚠ Há caractere(s) fora da tabela ASCII padrão (ex: acentos) — "
                "foram substituídos por '?' (0x3F) na conversão.\n\n"
            )

        formato = self.formato_var.get()
        if formato == "ascii_puro":
            self._render_ascii_puro(bytes_msg)
        elif formato == "rtu":
            self._render_rtu(bytes_msg)
        elif formato == "modbus_ascii":
            self._render_modbus_ascii(bytes_msg)

    def _render_ascii_puro(self, bytes_msg):
        hexstr = " ".join(f"{b:02X}" for b in bytes_msg)
        decstr = " ".join(str(b) for b in bytes_msg)
        self.trama_txt.insert(
            "end",
            f"Envio direto, sem framing de protocolo — {len(bytes_msg)} byte(s):\n\n"
            f"Em hexadecimal:\n{hexstr}\n\n"
            f"Em decimal:\n{decstr}"
        )

    def _render_rtu(self, bytes_msg):
        payload = bytes_msg
        tamanho = len(payload)
        corpo = bytes([self.ENDERECO_SIMULADO, self.FUNCAO_SIMULADA, tamanho]) + payload
        lo, hi = calcular_crc16_modbus(corpo)
        trama = corpo + bytes([lo, hi])
        hexstr = " ".join(f"{b:02X}" for b in trama)
        self.trama_txt.insert(
            "end",
            "Modbus RTU — binário puro na linha, sem delimitadores de texto "
            "(os equipamentos reconhecem o fim da trama pelo silêncio na "
            "linha, e a validam pelo CRC16):\n\n"
            f"[Endereço={self.ENDERECO_SIMULADO:02X}] "
            f"[Função={self.FUNCAO_SIMULADA:02X}] "
            f"[Tamanho={tamanho:02X}] [Dados...] "
            f"[CRC Lo={lo:02X} Hi={hi:02X}]\n\n"
            f"Bytes completos (hex), {len(trama)} byte(s):\n{hexstr}"
        )

    def _render_modbus_ascii(self, bytes_msg):
        payload = bytes_msg
        tamanho = len(payload)
        corpo = bytes([self.ENDERECO_SIMULADO, self.FUNCAO_SIMULADA, tamanho]) + payload
        lrc = calcular_lrc(corpo)
        corpo_completo = corpo + bytes([lrc])
        hex_chars = "".join(f"{b:02X}" for b in corpo_completo)
        trama_literal = f":{hex_chars}\r\n"
        bytes_no_fio = " ".join(f"{ord(c):02X}" for c in trama_literal)
        self.trama_txt.insert(
            "end",
            "Modbus ASCII — cada byte de dado vira 2 caracteres de texto em "
            "hexadecimal; a trama começa com ':' e termina com CRLF, e é "
            "validada por LRC (em vez de CRC16):\n\n"
            f"Trama literal enviada (como texto):\n{trama_literal!r}\n\n"
            f"Que corresponde a estes bytes reais no fio, {len(bytes_no_fio.split())} byte(s):\n"
            f"{bytes_no_fio}"
        )

    def _enviar(self):
        texto = self.texto_var.get()
        if not texto:
            return
        self._atualizar()
        agora = datetime.now().strftime("%H:%M:%S")
        rotulo_formato = {
            "ascii_puro": "ASCII puro",
            "rtu": "Modbus RTU",
            "modbus_ascii": "Modbus ASCII",
        }[self.formato_var.get()]
        self.historico.config(state="normal")
        self.historico.insert("end", f"[{agora}] ({rotulo_formato}) enviado: {texto}\n")
        self.historico.see("end")
        self.historico.config(state="disabled")

    def _fechar_tudo(self):
        self.janela1.destroy()

    def executar(self):
        self.janela1.mainloop()


if __name__ == "__main__":
    app = SimuladorTransmissao()
    app.executar()
