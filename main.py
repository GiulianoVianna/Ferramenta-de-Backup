import os
import platform
import sqlite3
import shutil
import time
import zipfile
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QTableWidgetItem, QSystemTrayIcon, QMenu, QMessageBox
from PyQt5.QtCore import QTime, pyqtSignal  
from datetime import datetime
from threading import Thread

# Cria o banco de dados SQLite
def criar_banco_de_dados():
    arquivo_db = "backup_dados.sqlite3"
    if os.path.exists(arquivo_db):
        return

    with sqlite3.connect(arquivo_db) as conexao:
        cursor = conexao.cursor()
        cursor.execute("""
        CREATE TABLE agendamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_backup TEXT,            
            origem TEXT,
            destino TEXT,
            horario TIME,
            status BOOLEAN
        )
        """)

# Janela para agendar backup
class AgendarWindow(QMainWindow):
    
    # Sinal para atualizar tabela ao salvar
    agendamento_atualizado = pyqtSignal()  
    
    def __init__(self, agendamento_id, horario_selecionado):
        super().__init__()
        uic.loadUi('agendar.ui', self)
        self.agendamento_id = agendamento_id  
        self.tm_horas.setTime(QTime.fromString(horario_selecionado, "HH:mm"))
        self.bt_salvar.clicked.connect(self.atualizar_agendamento)
   
    # Atualiza dados do agendamento no banco
    def atualizar_agendamento(self):
        
        # Obtem novo horário
        novo_horario = self.tm_horas.time().toString("HH:mm")
        
        # Atualiza no banco
        with sqlite3.connect('backup_dados.sqlite3') as conexao:
            cursor = conexao.cursor()
            cursor.execute("UPDATE agendamento SET horario = ? WHERE id = ?", (novo_horario, self.agendamento_id))
            
        # Emite sinal
        self.agendamento_atualizado.emit()
        self.close()

# Janela principal
class MainApp(QMainWindow):

    # Inicialização 
    def __init__(self):
        super().__init__()
        uic.loadUi('backup.ui', self)
        self.configurar_tray_icon()
        self.configurar_eventos()
        self.atualizar_tabela_agendamento()
        self.configurar_tamanho_colunas()
        self.encerrar_thread_agendamento = False
        self.tb_agendamento.doubleClicked.connect(self.abrir_janela_agendar)
        self.thread_agendamento = Thread(target=self.verificar_agendamentos, daemon=True)
        self.thread_agendamento.start()
        self.show()

    # Abre janela de agendamento ao clicar na tabela
    def abrir_janela_agendar(self):
        row_selecionada = self.tb_agendamento.currentRow()
        horario_selecionado = self.tb_agendamento.item(row_selecionada, 4).text()
        agendamento_id = self.tb_agendamento.item(row_selecionada, 0).text()
        self.janela_agendar = AgendarWindow(agendamento_id, horario_selecionado)
        self.janela_agendar.agendamento_atualizado.connect(self.atualizar_tabela_agendamento)  
        self.janela_agendar.show()

    # Exibe mensagem de status
    def exibir_mensagem_status(self, mensagem):
        self.lb_status.setText(mensagem)
        QApplication.processEvents()

    # Configura largura das colunas da tabela
    def configurar_tamanho_colunas(self):
        self.tb_agendamento.setColumnWidth(0, 0) 
        self.tb_agendamento.setColumnWidth(1, 160)
        self.tb_agendamento.setColumnWidth(2, 360)
        self.tb_agendamento.setColumnWidth(3, 360)
        self.tb_agendamento.setColumnWidth(4, 80)
        self.tb_agendamento.setColumnWidth(5, 120)

    # Configura ícone na bandeja do sistema
    def configurar_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.exibir_mensagem_status("A bandeja do sistema não é suportada nesta plataforma.")    
            return

        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        tray_menu = QMenu()
        tray_menu.addAction("Mostrar", self.show)
        tray_menu.addAction("Sair", self.sair_aplicacao)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    # Ação ao clicar no ícone da bandeja
    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Context:
            self.tray_icon.contextMenu().exec_(QCursor.pos())
        elif reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()

    # Sai do app
    def sair_aplicacao(self):
        self.exibir_mensagem_status("Saindo da aplicação.")
        self.encerrar_thread_agendamento = True
        self.tray_icon.hide()
        QApplication.instance().quit()

    # Vincula eventos da UI
    def configurar_eventos(self):
        self.bt_ad_origem.clicked.connect(self.selecionar_origem)
        self.bt_ad_destino.clicked.connect(self.selecionar_destino)
        self.bt_salvar.clicked.connect(self.salvar_agendamento)
        self.bt_excluir.clicked.connect(self.excluir_agendamento)

    # Seleciona diretório ou arquivo de origem
    def selecionar_origem(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Selecionar Origem")
        dialog.setText("Você deseja selecionar um arquivo ou diretório?")
        dialog.addButton("Arquivo", QMessageBox.AcceptRole)
        dialog.addButton("Diretório", QMessageBox.RejectRole)
        result = dialog.exec_()

        if result == QMessageBox.AcceptRole:
            origem, _ = QFileDialog.getOpenFileName(self, "Selecione o Arquivo de Origem")
        else:
            origem = QFileDialog.getExistingDirectory(self, "Selecione o Diretório de Origem")

        if origem:
            self.txt_origem.setText(origem)

    # Seleciona diretório de destino 
    def selecionar_destino(self):
        destino = QFileDialog.getExistingDirectory(self, "Selecione o Diretório de Destino")
        if destino:
            self.txt_destino.setText(destino)

    # Salva agendamento no banco
    def salvar_agendamento(self):
        origem = self.txt_origem.text()
        horario_agendado = self.tm_horas.text()
        destino = self.txt_destino.text() # Somente o diretório de destino
        status = self.rd_desligar.isChecked()
        nome_backup = self.txt_nome_backup.text().upper() # Nome do backup

        with sqlite3.connect('backup_dados.sqlite3') as conexao:
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO agendamento (origem, destino, horario, status, nome_backup) VALUES (?, ?, ?, ?, ?)", (origem, destino, horario_agendado, status, nome_backup))

        self.exibir_mensagem_status("Agendamento salvo com sucesso.")
        self.atualizar_tabela_agendamento()

    # Atualiza dados da tabela
    def atualizar_tabela_agendamento(self):
        with sqlite3.connect('backup_dados.sqlite3') as conexao:
            cursor = conexao.cursor()
            agendamentos = cursor.execute("SELECT id, nome_backup, origem, destino, horario, status FROM agendamento").fetchall()

        self.tb_agendamento.setRowCount(len(agendamentos))

        for row, agendamento in enumerate(agendamentos):
            self.tb_agendamento.setItem(row, 0, QTableWidgetItem(str(agendamento[0]))) # ID
            self.tb_agendamento.setItem(row, 1, QTableWidgetItem(agendamento[1]))      # Nome do Backup
            self.tb_agendamento.setItem(row, 2, QTableWidgetItem(agendamento[2]))      # Origem
            self.tb_agendamento.setItem(row, 3, QTableWidgetItem(agendamento[3]))      # Destino
            self.tb_agendamento.setItem(row, 4, QTableWidgetItem(agendamento[4]))      # Horário
            self.tb_agendamento.setItem(row, 5, QTableWidgetItem("Sim" if agendamento[5] else "Não")) # Status

    # Exclui agendamento
    def excluir_agendamento(self):
        row_selecionada = self.tb_agendamento.currentRow()
        if row_selecionada == -1:
            self.exibir_mensagem_status("Nenhum agendamento selecionado.")
            return

        agendamento_id = self.tb_agendamento.item(row_selecionada, 0).text()

        with sqlite3.connect('backup_dados.sqlite3') as conexao:
            cursor = conexao.cursor()
            cursor.execute("DELETE FROM agendamento WHERE id = ?", (agendamento_id,))

        self.exibir_mensagem_status("Agendamento excluído com sucesso.")
        self.atualizar_tabela_agendamento()

    # Realiza o backup
    def realizar_backup(self, origem, destino):
        if os.path.isdir(origem):
            shutil.make_archive(destino, 'zip', root_dir=origem)
        else:
            with zipfile.ZipFile(destino, 'w') as arquivo_zip:
                arquivo_zip.write(origem, os.path.basename(origem))
        self.exibir_mensagem_status(f"Backup realizado com sucesso em {destino}.")

    # Verifica agendamentos e dispara backups
    def verificar_agendamentos(self):
        while not self.encerrar_thread_agendamento:
            with sqlite3.connect('backup_dados.sqlite3') as conexao:
                cursor = conexao.cursor()
                agendamentos = cursor.execute("SELECT origem, destino, horario, status, nome_backup FROM agendamento").fetchall()

            hora_atual = datetime.now().strftime("%H:%M")

            for origem, destino_dir, horario, status, nome_backup in agendamentos:
                if horario == hora_atual:
                    timestamp_atual = datetime.now().strftime('%d-%m-%Y_%H_%M_%S') # Inclui data, hora, minuto e segundo
                    nome_arquivo = f"{nome_backup}_{timestamp_atual}.zip" # Adiciona extensão .zip
                    destino = os.path.join(destino_dir, nome_arquivo)  # Caminho completo do arquivo de destino
                    self.realizar_backup(origem, destino)
                    if status:
                        self.desligar_pc()

            if self.encerrar_thread_agendamento:
                break

            time.sleep(60)

    # Desliga o PC
    def desligar_pc(self):
        sistema_operacional = platform.system().lower()
        
        self.exibir_mensagem_status("Desligando o PC.")
        
        if sistema_operacional == "windows":
            os.system("shutdown /s /t 0")
        elif sistema_operacional == "linux":
            os.system("poweroff")
        else:
            print(f"Sistema operacional {sistema_operacional} não suportado. Desligamento não realizado.")

    # Ignora fechamento da janela principal se estiver minimizado 
    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()

if __name__ == '__main__':
    criar_banco_de_dados()
    app = QApplication([])
    window = MainApp()
    window.show()
    app.exec_()