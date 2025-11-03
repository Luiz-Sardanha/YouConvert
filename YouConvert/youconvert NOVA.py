import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import yt_dlp
import os
import shutil
import sys
import re
import urllib.parse
import queue
import concurrent.futures

def find_ffmpeg():
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")

class PlaylistDownloader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Downloader de Mídia")
        self.root.geometry("850x600")
        self.root.configure(bg="#f0f0f0")
        
        # Variáveis
        self.entries = []
        self.video_info = []
        self.cancelled = False
        self.ffmpeg_path = find_ffmpeg()
        self.download_queue = queue.Queue()
        self.workers = []
        self.max_workers = 3  # Número máximo de downloads paralelos
        
        # Variáveis para o modo de acumulação
        self.accumulation_active = False  # Estado do modo de acumulação
        self.original_entry_count = 0     # Contador para saber quantos novos itens foram adicionados
        
        # Criar estilo para botões
        self.style = ttk.Style()
        self.style.configure("Accent.TButton", background="#0d6efd")
        self.style.configure("Success.TButton", background="#28a745")
        self.style.configure("Warning.TButton", background="#ffc107")
        self.style.configure("Danger.TButton", background="#dc3545")
        
        self.setup_ui()
        
        # Perguntar antes de fechar se houver downloads pendentes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Seção URL
        url_frame = ttk.LabelFrame(main_frame, text="URL")
        url_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=5)
        main_frame.columnconfigure(0, weight=1)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.url_entry = ttk.Entry(url_frame, width=70)
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        url_frame.columnconfigure(1, weight=1)
        
        # Seleção de plataforma (agora apenas visual, usaremos automático)
        platform_frame = ttk.Frame(url_frame)
        platform_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=5, padx=5)
        
        ttk.Label(platform_frame, text="Plataformas suportadas:").pack(side="left")
        ttk.Label(platform_frame, text="YouTube", foreground="#FF0000").pack(side="left", padx=(5, 0))
        ttk.Label(platform_frame, text="•", foreground="#888888").pack(side="left", padx=(5, 0))
        ttk.Label(platform_frame, text="YouTube Music", foreground="#FF0000").pack(side="left", padx=(5, 0))
        ttk.Label(platform_frame, text="•", foreground="#888888").pack(side="left", padx=(5, 0))
        ttk.Label(platform_frame, text="Instagram", foreground="#E1306C").pack(side="left", padx=(5, 0))
        ttk.Label(platform_frame, text="•", foreground="#888888").pack(side="left", padx=(5, 0))
        ttk.Label(platform_frame, text="Facebook", foreground="#4267B2").pack(side="left", padx=(5, 0))
        
        # Botões de ação para URL
        scan_frame = ttk.Frame(url_frame)
        scan_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=5, padx=5)
        
        # Botão principal de escanear
        self.scan_btn = ttk.Button(
            scan_frame, 
            text="Escanear URL", 
            command=self.scan_playlist
        )
        self.scan_btn.pack(side="left", padx=(0, 5))
        
        # Botão para ativar/desativar modo de acumulação
        self.accumulate_btn = ttk.Button(
            scan_frame,
            text="Modo Acumulação: OFF",
            command=self.toggle_accumulation_mode
        )
        self.accumulate_btn.pack(side="left", padx=(0, 5))
        
        # Botão para limpar lista
        self.clear_btn = ttk.Button(
            scan_frame,
            text="Limpar Lista",
            command=self.clear_list,
            state="disabled"
        )
        self.clear_btn.pack(side="left", padx=(0, 5))
        
        # Contadores e informações
        self.count_label = ttk.Label(scan_frame, text="Arquivos: 0")
        self.count_label.pack(side="left", padx=10)
        
        # Indicador de tipo detectado (playlist/vídeo)
        self.content_type_label = ttk.Label(scan_frame, text="")
        self.content_type_label.pack(side="left", padx=10)
        
        # Seção de destino
        dest_frame = ttk.LabelFrame(main_frame, text="Destino")
        dest_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=5)
        
        self.dest_entry = ttk.Entry(dest_frame)
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # Definir pasta padrão
        music_dir = os.path.join(os.path.expanduser("~"), "Music")
        if os.path.exists(music_dir):
            self.dest_entry.insert(0, music_dir)
        else:
            self.dest_entry.insert(0, os.path.expanduser("~"))
            
        ttk.Button(dest_frame, text="Explorar", command=self.choose_folder).pack(side="left", padx=5, pady=5)
        
        # Opções de formato
        options_frame = ttk.LabelFrame(main_frame, text="Opções")
        options_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=5)
        
        # Layout de 2 colunas para opções
        left_options = ttk.Frame(options_frame)
        left_options.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        right_options = ttk.Frame(options_frame)
        right_options.pack(side="right", fill="x", expand=True, padx=5, pady=5)
        
        # Seleção de formato (coluna esquerda)
        format_frame = ttk.Frame(left_options)
        format_frame.pack(fill="x", pady=5)
        
        ttk.Label(format_frame, text="Formato:").pack(side="left")
        self.format_var = tk.StringVar(value="MP3")
        ttk.Radiobutton(format_frame, text="MP3", variable=self.format_var, value="MP3", 
                      command=self.toggle_format_options).pack(side="left", padx=(5, 10))
        ttk.Radiobutton(format_frame, text="MP4", variable=self.format_var, value="MP4", 
                      command=self.toggle_format_options).pack(side="left")
        
        # Container para opções de formato
        self.format_options_frame = ttk.Frame(left_options)
        self.format_options_frame.pack(fill="x", pady=5)
        
        # Opções MP3
        self.mp3_frame = ttk.Frame(self.format_options_frame)
        ttk.Label(self.mp3_frame, text="Qualidade MP3:").pack(side="left")
        self.mp3_quality = ttk.Combobox(self.mp3_frame, values=["128", "192", "256", "320"], 
                                       width=5, state="readonly")
        self.mp3_quality.pack(side="left", padx=5)
        self.mp3_quality.current(3)  # 320 kbps por padrão
        
        # Opções MP4
        self.mp4_frame = ttk.Frame(self.format_options_frame)
        ttk.Label(self.mp4_frame, text="Resolução:").pack(side="left")
        self.mp4_resolution = ttk.Combobox(self.mp4_frame, 
                                          values=["Melhor qualidade", "2160p", "1440p", "1080p", "720p", "480p", "360p"], 
                                          width=15, state="readonly")
        self.mp4_resolution.pack(side="left", padx=5)
        self.mp4_resolution.current(0)  # Melhor qualidade por padrão
        
        # Opções de velocidade (coluna direita)
        ttk.Label(right_options, text="Downloads paralelos:").pack(side="left")
        self.parallel_var = tk.IntVar(value=3)
        self.parallel_spinbox = ttk.Spinbox(right_options, from_=1, to=10, width=3, textvariable=self.parallel_var)
        self.parallel_spinbox.pack(side="left", padx=5)
        
        # Opção para tentar novamente downloads falhos
        self.retry_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_options, text="Tentar novamente downloads falhos (até 3x)", 
                       variable=self.retry_var).pack(side="left", padx=(20, 0))
        
        # Ativar opção inicial
        self.toggle_format_options()
        
        # Barra de progresso geral
        progress_frame = ttk.LabelFrame(main_frame, text="Progresso")
        progress_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=5)
        
        self.status_label = ttk.Label(progress_frame, text="Aguardando...")
        self.status_label.pack(anchor="w", pady=5, padx=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=100, mode="determinate")
        self.progress_bar.pack(fill="x", pady=5, padx=5)
        
        # Lista de arquivos
        files_frame = ttk.LabelFrame(main_frame, text="Lista de arquivos")
        files_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0, 10), padx=5)
        main_frame.rowconfigure(4, weight=1)
        
        self.files_list = ttk.Treeview(files_frame, 
                                     columns=("Título", "Duração", "Plataforma", "Status", "Ação"), 
                                     show="headings", 
                                     height=10)
        
        self.files_list.heading("Título", text="Título")
        self.files_list.heading("Duração", text="Duração")
        self.files_list.heading("Plataforma", text="Plataforma")
        self.files_list.heading("Status", text="Status")
        self.files_list.heading("Ação", text="Ação")
        
        self.files_list.column("Título", width=300, minwidth=200)
        self.files_list.column("Duração", width=80, anchor="center")
        self.files_list.column("Plataforma", width=120, anchor="center")
        self.files_list.column("Status", width=100, anchor="center")
        self.files_list.column("Ação", width=80, anchor="center")
        
        scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.files_list.yview)
        self.files_list.configure(yscrollcommand=scrollbar.set)
        
        self.files_list.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        self.files_list.bind("<ButtonRelease-1>", self.on_files_list_click)
        
        # Log de mensagens
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=5)
        
        self.log_text = tk.Text(log_frame, height=4, width=50, wrap="word", bg="#f5f5f5", state="disabled")
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        log_scrollbar.pack(side="right", fill="y", pady=5)
        
        # Botões de ação
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(5, 0), padx=5)
        
        # Botões para download e controle
        self.download_btn = ttk.Button(
            btn_frame, 
            text="Baixar Tudo", 
            command=self.start_download,
            style="Success.TButton"
        )
        self.download_btn.pack(side="left", padx=(0, 5))
        
        self.retry_btn = ttk.Button(
            btn_frame, 
            text="Tentar Baixar Falhas", 
            command=self.retry_failed_downloads, 
            state="disabled",
            style="Warning.TButton"
        )
        self.retry_btn.pack(side="left", padx=(0, 5))
        
        self.cancel_btn = ttk.Button(
            btn_frame, 
            text="Cancelar", 
            command=self.cancel_download, 
            state="disabled",
            style="Danger.TButton"
        )
        self.cancel_btn.pack(side="left")
        
        # Botão para abrir pasta de destino
        ttk.Button(btn_frame, text="Abrir Pasta", command=self.open_dest_folder).pack(side="right")
        
        # Verificar se ffmpeg está instalado
        if not self.ffmpeg_path:
            self.add_to_log("AVISO: ffmpeg não encontrado! Necessário para conversão de áudio.")
    
    def add_to_log(self, message):
        """Adiciona mensagem ao log"""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
    
    def toggle_format_options(self):
        if self.format_var.get() == "MP3":
            self.mp4_frame.pack_forget()
            self.mp3_frame.pack(fill="x")
        else:
            self.mp3_frame.pack_forget()
            self.mp4_frame.pack(fill="x")
    
    def toggle_accumulation_mode(self):
        """Alterna entre modo normal e modo de acumulação"""
        self.accumulation_active = not self.accumulation_active
        
        if self.accumulation_active:
            self.accumulate_btn.config(text="Modo Acumulação: ON", style="Accent.TButton")
            self.status_label.config(text="Modo de acumulação ATIVADO. Escaneie várias URLs para adicionar à lista.")
            self.add_to_log("MODO ACUMULAÇÃO: ATIVADO. Você pode adicionar múltiplas músicas à lista antes de baixar.")
        else:
            self.accumulate_btn.config(text="Modo Acumulação: OFF")
            self.status_label.config(text="Modo de acumulação DESATIVADO.")
            self.add_to_log("MODO ACUMULAÇÃO: DESATIVADO.")
    
    def clear_list(self):
        """Limpa a lista de itens"""
        if not self.entries:
            return
            
        # Confirmar com o usuário
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja limpar a lista de downloads?"):
            for item in self.files_list.get_children():
                self.files_list.delete(item)
                
            self.entries = []
            self.video_info = []
            self.count_label.config(text="Arquivos: 0")
            self.content_type_label.config(text="")
            self.status_label.config(text="Lista limpa.")
            self.add_to_log("Lista de arquivos limpa.")
            self.clear_btn.config(state="disabled")
            self.download_btn.config(state="disabled")
    
    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, folder)
    
    def open_dest_folder(self):
        dest = self.dest_entry.get()
        if os.path.exists(dest):
            if sys.platform == 'win32':
                os.startfile(dest)
            elif sys.platform == 'darwin':  # macOS
                import subprocess
                subprocess.Popen(['open', dest])
            else:  # Linux
                import subprocess
                subprocess.Popen(['xdg-open', dest])
    
    def format_duration(self, seconds):
        if not seconds:
            return "--:--"
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def is_playlist_url(self, url):
        """Verifica se a URL parece ser de uma playlist"""
        return ('list=' in url or 
                'playlist' in url or 
                '/sets/' in url)  # Para SoundCloud

    def fix_youtube_music_url(self, url):
        """Corrige URLs do YouTube Music para extrair corretamente"""
        # NOVA LÓGICA: Detectar playlists de mix (RDAT...) e extrair apenas o vídeo
        if "music.youtube.com" in url or "youtube.com" in url:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # Verificar se tem parâmetro de playlist
            if "list" in query_params:
                playlist_id = query_params["list"][0]
                
                # Verificar se é um mix do YouTube (começando com RDAT, RDAMVM, etc.)
                is_mix = playlist_id.startswith(("RDAT", "RDAMVM", "RDAMPL"))
                
                if is_mix and "v" in query_params:
                    # Para mixes, extrair apenas o ID do vídeo (ignorar a playlist)
                    video_id = query_params["v"][0]
                    fixed_url = f"https://music.youtube.com/watch?v={video_id}"
                    self.add_to_log(f"Detectada playlist de mix. Extraindo apenas o vídeo atual: {fixed_url}")
                    
                    # Informar o usuário sobre a limitação
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Aviso - Playlist de Mix", 
                        "As playlists de 'mix' do YouTube não podem ser baixadas completamente.\n\n"
                        "Apenas o vídeo atual será extraído. Para baixar mais músicas do mix, "
                        "você pode ativar o Modo Acumulação e adicionar várias músicas do mix individualmente."
                    ))
                    return fixed_url
                
                elif "music.youtube.com" in url and not is_mix:
                    # Para playlists normais do YouTube Music
                    fixed_url = f"https://music.youtube.com/playlist?list={playlist_id}"
                    self.add_to_log(f"Corrigindo URL do YouTube Music: {fixed_url}")
                    return fixed_url
        
        # Se não precisa de correção, retornar a URL original
        return url
    
    def detect_platform(self, url):
        """Detecta a plataforma com base na URL"""
        if "youtube.com" in url or "youtu.be" in url:
            if "music.youtube.com" in url:
                return "YouTube Music"
            return "YouTube"
        elif "instagram.com" in url:
            return "Instagram"
        elif "facebook.com" in url or "fb.watch" in url:
            return "Facebook"
        elif "twitter.com" in url:
            return "Twitter"
        elif "soundcloud.com" in url:
            return "SoundCloud"
        else:
            return "Desconhecido"
    
    def scan_playlist(self):
        original_url = self.url_entry.get().strip()
        if not original_url:
            messagebox.showwarning("Aviso", "Insira uma URL válida primeiro.")
            return
        
        # Se estamos no modo de acumulação, não limpar a lista anterior
        if not self.accumulation_active:
            # Modo normal: limpar lista existente
            self.entries = []
            self.video_info = []
            for item in self.files_list.get_children():
                self.files_list.delete(item)
            self.original_entry_count = 0
        else:
            # Modo acumulação: guardar quantos itens já temos para relatar novos itens depois
            self.original_entry_count = len(self.entries)
            
        # Limpar campo de entrada após escanear para facilitar colar próxima URL
        url_to_scan = original_url  # Guardar antes de limpar
        self.url_entry.delete(0, tk.END)
        
        self.status_label.config(text="Escaneando...")
        self.add_to_log(f"Escaneando: {original_url}")
        
        def do_scan():
            try:
                # Detectar se é playlist
                is_playlist = self.is_playlist_url(url_to_scan)
                
                # Determinar plataforma automaticamente
                detected_platform = self.detect_platform(url_to_scan)
                self.add_to_log(f"Plataforma detectada: {detected_platform}")
                
                # Tratamento especial para URLs
                url = self.fix_youtube_music_url(url_to_scan)
                is_modified_url = url != url_to_scan
                
                # Atualizar flag de playlist se a URL foi modificada para vídeo único
                if is_modified_url and "list=" not in url:
                    is_playlist = False
                
                # Opções para yt-dlp
                ydl_opts = {
                    'quiet': True, 
                    'skip_download': True,
                    'extract_flat': True if is_playlist else False,
                    'noplaylist': not is_playlist,
                    'dump_single_json': True,
                    'force_generic_extractor': False,
                    'ignoreerrors': True  # Ignorar erros para que possa continuar mesmo com alguns problemas
                }
                
                # Para YouTube Music e playlists, força extração
                if is_playlist:
                    ydl_opts['yes_playlist'] = True
                    if detected_platform == "YouTube Music":
                        ydl_opts['extract_flat'] = "in_playlist"
                        
                # Capturar saída para log
                def my_logger(msg):
                    if msg.startswith('[download]'):
                        return  # Ignorar mensagens de download
                    if "WARNING:" in msg or "ERROR:" in msg:
                        self.root.after(0, lambda: self.add_to_log(msg.strip()))
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.params['logger'] = type('Logger', (), {'debug': my_logger, 'info': my_logger, 'warning': my_logger, 'error': my_logger})
                    info = ydl.extract_info(url, download=False)
                
                # Extrair informações
                entries = []
                if 'entries' in info and info['entries']:
                    entries = info['entries']
                    
                    if self.accumulation_active:
                        # No modo acumulação, atualizar o tipo apenas se for o primeiro scan
                        if self.original_entry_count == 0:
                            self.content_type_label.config(text=f"Tipo: Acumulando itens")
                    else:
                        self.content_type_label.config(text=f"Tipo: Playlist com {len(entries)} itens")
                        
                    self.add_to_log(f"Playlist detectada com {len(entries)} itens")
                else:
                    entries = [info]
                    if not self.accumulation_active or self.original_entry_count == 0:
                        self.content_type_label.config(text="Tipo: Vídeo/Áudio único")
                    self.add_to_log("Item único detectado")
                
                valid_entries = 0
                for entry in entries:
                    if entry is None:  # Pular entradas inválidas
                        continue
                        
                    # Obter URL ou ID
                    entry_url = entry.get('url') or entry.get('id')
                    if not entry_url:
                        continue
                    
                    # Para YouTube e YouTube Music, garanta URL completa
                    if detected_platform in ["YouTube", "YouTube Music"]:
                        if 'id' in entry and not entry_url.startswith('http'):
                            if detected_platform == "YouTube Music":
                                entry_url = f"https://music.youtube.com/watch?v={entry['id']}"
                            else:
                                entry_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        
                    self.entries.append(entry_url)
                    
                    # Obter informações disponíveis
                    video_info = {
                        'id': entry.get('id', ""),
                        'title': entry.get('title', 'Desconhecido'),
                        'duration': entry.get('duration'),
                        'uploader': entry.get('uploader', 'Desconhecido'),
                        'platform': detected_platform,
                        'status': 'Pendente'
                    }
                    self.video_info.append(video_info)
                    
                    # Adicionar à lista com botão mais explícito
                    item_id = self.files_list.insert("", "end", values=(
                        video_info['title'],
                        self.format_duration(video_info['duration']),
                        video_info['platform'],
                        "Pendente",
                        "⬇️ Baixar"  # Texto mais claro para o botão de download
                    ))
                    valid_entries += 1
                
                # Atualizar contadores e interface
                total_items = len(self.entries)
                new_items = total_items - self.original_entry_count
                
                self.count_label.config(text=f"Arquivos: {total_items}")
                
                # Habilitar botões relevantes
                if total_items > 0:
                    self.download_btn.config(state="normal")
                    self.clear_btn.config(state="normal")
                
                # Mensagens para o usuário
                if self.accumulation_active and valid_entries > 0:
                    # Modo acumulação: mostrar quantos novos itens foram adicionados
                    self.status_label.config(
                        text=f"Acumulação: {new_items} novos itens adicionados (Total: {total_items}). Escaneie mais ou clique em 'Baixar Tudo'."
                    )
                    self.add_to_log(f"Acumulação: Adicionados {new_items} novos itens à lista (Total: {total_items})")
                    
                    # Mostrar janela informativa
                    if new_items > 0:
                        messagebox.showinfo(
                            "Itens Adicionados", 
                            f"Foram adicionados {new_items} novos itens à lista.\n"
                            f"Total de itens na lista: {total_items}\n\n"
                            "Você pode adicionar mais itens ou clicar em 'Baixar Tudo' quando estiver pronto."
                        )
                elif valid_entries > 0:
                    # Modo normal
                    self.status_label.config(
                        text=f"Lista pronta: {valid_entries} itens. Baixe individualmente clicando em '⬇️ Baixar' ou use 'Baixar Tudo'."
                    )
                    self.add_to_log(f"Lista pronta com {valid_entries} itens.")
                else:
                    # Nenhum item encontrado
                    self.add_to_log("AVISO: Nenhum item válido encontrado!")
                    messagebox.showwarning("Aviso", "Nenhum item válido foi encontrado na URL.")
                
            except Exception as e:
                error_msg = str(e)
                self.add_to_log(f"ERRO: {error_msg}")
                messagebox.showerror("Erro", f"Erro ao escanear: {error_msg}")
                self.status_label.config(text="Erro ao escanear.")
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def start_download(self):
        if not self.entries:
            messagebox.showwarning("Aviso", "Escaneie a playlist primeiro.")
            return
        
        dest = self.dest_entry.get().strip()
        if not dest:
            messagebox.showwarning("Aviso", "Selecione uma pasta de destino.")
            return
        
        self.download_btn.config(state="disabled")
        self.retry_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.scan_btn.config(state="disabled")
        self.accumulate_btn.config(state="disabled")
        self.cancelled = False
        
        # Limpar fila de download anterior
        while not self.download_queue.empty():
            self.download_queue.get()
        
        # Atualizar número máximo de workers
        self.max_workers = self.parallel_var.get()
        
        # Resetar status dos arquivos
        for i, item in enumerate(self.files_list.get_children()):
            self.files_list.item(item, values=(
                self.files_list.item(item)['values'][0],
                self.files_list.item(item)['values'][1],
                self.files_list.item(item)['values'][2],
                "Aguardando",
                "⏸"  # Muda o ícone enquanto download está pendente
            ))
            self.video_info[i]['status'] = 'Aguardando'
        
        # Iniciar download em threads
        format_type = self.format_var.get()
        quality = self.mp3_quality.get() if format_type == "MP3" else None
        resolution = self.mp4_resolution.get() if format_type == "MP4" else None
        
        # Enfileirar todos os itens para download
        for i in range(len(self.entries)):
            self.download_queue.put(i)
        
        # Iniciar worker threads
        self.workers = []
        for _ in range(min(self.max_workers, len(self.entries))):
            worker = threading.Thread(
                target=self.download_worker,
                args=(dest, format_type, quality, resolution),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        # Thread para monitorar progresso geral
        threading.Thread(target=self.monitor_progress, daemon=True).start()
    
    def download_worker(self, dest_folder, format_type, quality=None, resolution=None):
        """Worker thread para baixar itens da fila"""
        while not self.cancelled:
            try:
                # Tentar obter um item da fila (sem bloquear)
                try:
                    idx = self.download_queue.get(block=False)
                except queue.Empty:
                    # Fila vazia, sair do loop
                    break
                
                # Obter informações do item
                url = self.entries[idx]
                info = self.video_info[idx]
                item = self.files_list.get_children()[idx]
                
                # Atualizar status
                self.root.after(0, lambda: self.files_list.item(item, values=(
                    info['title'],
                    self.files_list.item(item)['values'][1],
                    info['platform'],
                    "Baixando...",
                    "⏳"
                )))
                self.root.after(0, lambda: self.add_to_log(f"Iniciando download: {info['title']}"))
                
                # Configurar opções de download
                outtmpl = os.path.join(dest_folder, '%(title)s.%(ext)s')
                
                if format_type == "MP3":
                    postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': quality}]
                    format_opt = 'bestaudio/best'
                else:
                    postprocessors = []
                    if resolution and resolution != "Melhor qualidade":
                        height = resolution.split("p")[0]
                        format_opt = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
                    else:
                        format_opt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
                
                # Configurar callback para progresso
                def progress_hook(d):
                    if d['status'] == 'finished':
                        # Atualizar item na lista como concluído
                        self.root.after(0, lambda: self.files_list.item(item, values=(
                            info['title'],
                            self.files_list.item(item)['values'][1],
                            info['platform'],
                            "Concluído",
                            "✅"
                        )))
                
                # Opções de download
                ydl_opts = {
                    'format': format_opt,
                    'outtmpl': outtmpl,
                    'postprocessors': postprocessors,
                    'noplaylist': True,  # Já estamos processando cada item individualmente
                    'ignoreerrors': True,
                    'progress_hooks': [progress_hook],
                    'quiet': True,
                    'ffmpeg_location': self.ffmpeg_path
                }
                
                # Registrar erros
                error_log = []
                def log_error(msg):
                    error_log.append(msg)
                    
                ydl_opts['logger'] = type('Logger', (), {
                    'debug': lambda msg: None,
                    'info': lambda msg: None,
                    'warning': log_error,
                    'error': log_error
                })
                
                # Tentar download com até 3 tentativas se habilitado
                max_retries = 3 if self.retry_var.get() else 1
                success = False
                
                for attempt in range(max_retries):
                    if self.cancelled:
                        break
                        
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                        
                        # Verificar se houve erros críticos
                        if any("ERROR:" in msg for msg in error_log):
                            error_msg = next((msg for msg in error_log if "ERROR:" in msg), "Erro desconhecido")
                            raise Exception(error_msg)
                            
                        success = True
                        self.root.after(0, lambda: self.add_to_log(f"✓ Download concluído: {info['title']}"))
                        break  # Sair do loop de tentativas
                        
                    except Exception as e:
                        error_msg = str(e)
                        if attempt < max_retries - 1:  # Se não é a última tentativa
                            self.root.after(0, lambda: self.add_to_log(
                                f"Tentativa {attempt+1} falhou para '{info['title']}'. Tentando novamente..."))
                            time.sleep(1)  # Aguardar antes de tentar novamente
                        else:
                            self.root.after(0, lambda: self.add_to_log(
                                f"✗ Erro ao baixar '{info['title']}' após {max_retries} tentativas: {error_msg}"))
                
                # Atualizar status final
                if success:
                    info['status'] = 'Concluído'
                    self.root.after(0, lambda: self.files_list.item(item, values=(
                        info['title'],
                        self.files_list.item(item)['values'][1],
                        info['platform'],
                        "Concluído",
                        "✅"
                    )))
                else:
                    info['status'] = 'Erro'
                    self.root.after(0, lambda: self.files_list.item(item, values=(
                        info['title'],
                        self.files_list.item(item)['values'][1],
                        info['platform'],
                        "Erro",
                        "❌"
                    )))
                
                # Marcar como concluído na fila
                self.download_queue.task_done()
                
            except Exception as e:
                self.root.after(0, lambda: self.add_to_log(f"Erro no worker: {str(e)}"))
                # Em caso de erro inesperado, apenas continuar para o próximo item
                try:
                    self.download_queue.task_done()
                except:
                    pass
    
    def monitor_progress(self):
        """Monitora o progresso geral dos downloads"""
        total = len(self.entries)
        
        while not self.cancelled:
            # Contar itens por status
            statuses = {'Aguardando': 0, 'Baixando...': 0, 'Concluído': 0, 'Erro': 0}
            
            for info in self.video_info:
                if info['status'] in statuses:
                    statuses[info['status']] += 1
            
            # Atualizar barra de progresso
            completed = statuses['Concluído'] + statuses['Erro']
            progress_pct = (completed / total) * 100 if total > 0 else 0
            self.progress_bar['value'] = progress_pct
            
            # Atualizar rótulo de status
            status_text = (f"Progresso: {completed}/{total} ({int(progress_pct)}%) - "
                           f"Concluídos: {statuses['Concluído']}, "
                           f"Erros: {statuses['Erro']}")
            self.status_label.config(text=status_text)
            
            # Verificar se terminou
            if completed >= total:
                break
                
            # Verificar se todos os workers estão parados
            all_workers_done = all(not worker.is_alive() for worker in self.workers)
            if all_workers_done and self.download_queue.empty():
                break
                
            time.sleep(0.2)
        
        # Atualizações finais da UI
        if self.cancelled:
            self.status_label.config(text="Download cancelado.")
            self.add_to_log("Download cancelado pelo usuário")
        else:
            # Contar itens finais por status
            completed = sum(1 for info in self.video_info if info['status'] in ['Concluído', 'Erro'])
            success_count = sum(1 for info in self.video_info if info['status'] == 'Concluído')
            error_count = sum(1 for info in self.video_info if info['status'] == 'Erro')
            
            self.status_label.config(text=f"Download concluído. Sucesso: {success_count}, Erros: {error_count}")
            self.add_to_log(f"Todos os downloads concluídos. Sucesso: {success_count}, Erros: {error_count}")
            
            # Habilitar botão para tentar novamente se houver erros
            if error_count > 0:
                self.retry_btn.config(state="normal")
        
        # Reabilitar botões após download
        self.download_btn.config(state="normal")
        self.scan_btn.config(state="normal")
        self.accumulate_btn.config(state="normal")
        self.clear_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
    
    def cancel_download(self):
        """Cancela todos os downloads ativos"""
        self.cancelled = True
        self.cancel_btn.config(state="disabled")
        self.status_label.config(text="Cancelando download...")
        self.add_to_log("Cancelando downloads...")
    
    def retry_failed_downloads(self):
        """Tenta novamente baixar os itens que falharam"""
        failed_indexes = [i for i, info in enumerate(self.video_info) if info['status'] == 'Erro']
        
        if not failed_indexes:
            messagebox.showinfo("Informação", "Não há downloads falhos para tentar novamente.")
            return
        
        # Enfileirar apenas os falhos
        for idx in failed_indexes:
            self.download_queue.put(idx)
            
            # Atualizar status na lista
            item = self.files_list.get_children()[idx]
            self.files_list.item(item, values=(
                self.video_info[idx]['title'],
                self.files_list.item(item)['values'][1],
                self.video_info[idx]['platform'],
                "Aguardando",
                "⏸"
            ))
            self.video_info[idx]['status'] = 'Aguardando'
        
        # Configurações
        dest = self.dest_entry.get().strip()
        format_type = self.format_var.get()
        quality = self.mp3_quality.get() if format_type == "MP3" else None
        resolution = self.mp4_resolution.get() if format_type == "MP4" else None
        
        # Desabilitar botões
        self.download_btn.config(state="disabled")
        self.retry_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self.scan_btn.config(state="disabled")
        self.accumulate_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.cancelled = False
        
        # Iniciar workers
        self.workers = []
        for _ in range(min(self.max_workers, len(failed_indexes))):
            worker = threading.Thread(
                target=self.download_worker,
                args=(dest, format_type, quality, resolution),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        # Monitorar progresso
        threading.Thread(target=self.monitor_progress, daemon=True).start()
    
    def download_single_item(self, idx):
        """Baixa um único item da lista"""
        if idx < 0 or idx >= len(self.entries):
            return
            
        # Verificar se já foi baixado com sucesso
        if self.video_info[idx]['status'] == 'Concluído':
            response = messagebox.askyesno("Confirmar", 
                                          "Este item já foi baixado. Deseja baixá-lo novamente?")
            if not response:
                return
        
        # Configurações
        dest = self.dest_entry.get().strip()
        if not dest:
            messagebox.showwarning("Aviso", "Selecione uma pasta de destino.")
            return
            
        format_type = self.format_var.get()
        quality = self.mp3_quality.get() if format_type == "MP3" else None
        resolution = self.mp4_resolution.get() if format_type == "MP4" else None
        
        # Atualizar status na lista
        item = self.files_list.get_children()[idx]
        self.files_list.item(item, values=(
            self.video_info[idx]['title'],
            self.files_list.item(item)['values'][1],
            self.video_info[idx]['platform'],
            "Baixando...",
            "⏳"
        ))
        self.video_info[idx]['status'] = 'Baixando...'
        
        # Iniciar download em thread separada
        threading.Thread(
            target=self.download_single_worker,
            args=(idx, dest, format_type, quality, resolution),
            daemon=True
        ).start()
    
    def download_single_worker(self, idx, dest_folder, format_type, quality=None, resolution=None):
        """Worker para baixar um único item"""
        url = self.entries[idx]
        info = self.video_info[idx]
        item = self.files_list.get_children()[idx]
        
        self.add_to_log(f"Iniciando download individual: {info['title']}")
        
        # Configurar opções de download
        outtmpl = os.path.join(dest_folder, '%(title)s.%(ext)s')
        
        if format_type == "MP3":
            postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': quality}]
            format_opt = 'bestaudio/best'
        else:
            postprocessors = []
            if resolution and resolution != "Melhor qualidade":
                height = resolution.split("p")[0]
                format_opt = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            else:
                format_opt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
        
        # Opções de download
        ydl_opts = {
            'format': format_opt,
            'outtmpl': outtmpl,
            'postprocessors': postprocessors,
            'noplaylist': True,  # Já estamos processando cada item individualmente
            'ignoreerrors': True,
            'quiet': True,
            'ffmpeg_location': self.ffmpeg_path
        }
        
        # Registrar erros
        error_log = []
        def log_error(msg):
            error_log.append(msg)
            
        ydl_opts['logger'] = type('Logger', (), {
            'debug': lambda msg: None,
            'info': lambda msg: None,
            'warning': log_error,
            'error': log_error
        })
        
        # Tentar download com até 3 tentativas
        max_retries = 3 if self.retry_var.get() else 1
        success = False
        
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Verificar se houve erros
                if any("ERROR:" in msg for msg in error_log):
                    error_msg = next((msg for msg in error_log if "ERROR:" in msg), "Erro desconhecido")
                    raise Exception(error_msg)
                    
                success = True
                self.add_to_log(f"✓ Download individual concluído: {info['title']}")
                break  # Sair do loop de tentativas
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:  # Se não é a última tentativa
                    self.add_to_log(
                        f"Tentativa {attempt+1} falhou para '{info['title']}'. Tentando novamente...")
                    time.sleep(1)  # Aguardar antes de tentar novamente
                else:
                    self.add_to_log(
                        f"✗ Erro ao baixar '{info['title']}' após {max_retries} tentativas: {error_msg}")
        
        # Atualizar status final
        if success:
            info['status'] = 'Concluído'
            self.files_list.item(item, values=(
                info['title'],
                self.files_list.item(item)['values'][1],
                info['platform'],
                "Concluído",
                "✅"
            ))
            
            # Informar o usuário
            self.root.after(0, lambda: messagebox.showinfo(
                "Download Concluído",
                f"O download de '{info['title']}' foi concluído com sucesso.\n\n"
                f"Salvo em: {dest_folder}"
            ))
        else:
            info['status'] = 'Erro'
            self.files_list.item(item, values=(
                info['title'],
                self.files_list.item(item)['values'][1],
                info['platform'],
                "Erro",
                "❌"
            ))
            
            # Informar o usuário sobre o erro
            self.root.after(0, lambda: messagebox.showerror(
                "Erro no Download",
                f"Não foi possível baixar '{info['title']}'.\n\n"
                f"Por favor, tente novamente ou verifique o log para mais detalhes."
            ))
    
    def on_files_list_click(self, event):
        """Gerencia cliques na lista de arquivos"""
        region = self.files_list.identify("region", event.x, event.y)
        if region == "cell":
            column = self.files_list.identify_column(event.x)
            row = self.files_list.identify_row(event.y)
            
            if not row:
                return
                
            item_idx = self.files_list.index(row)
            
            # Se clicou na coluna de ação
            if column == "#5":  # Coluna "Ação"
                self.download_single_item(item_idx)
            # Adicionando suporte para clique duplo em qualquer coluna
            elif event.num == 2:  # Clique duplo
                self.download_single_item(item_idx)
    
    def on_closing(self):
        """Manipulador de evento ao fechar a aplicação"""
        # Verificar se há downloads em andamento
        downloads_active = any(worker.is_alive() for worker in self.workers)
        has_pending = any(info['status'] in ['Pendente', 'Aguardando'] for info in self.video_info)
        
        if downloads_active:
            response = messagebox.askyesno(
                "Confirmar Saída", 
                "Existem downloads em andamento. Tem certeza que deseja sair?\n\n"
                "Os downloads serão cancelados."
            )
            if response:
                self.cancelled = True
                self.root.destroy()
        elif has_pending and self.entries:
            response = messagebox.askyesno(
                "Confirmar Saída", 
                "Existem itens pendentes na lista. Tem certeza que deseja sair?"
            )
            if response:
                self.root.destroy()
        else:
            self.root.destroy()
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    try:
        # Verificar dependências
        import yt_dlp
    except ImportError:
        print("Erro: yt-dlp não está instalado. Instale com 'pip install yt-dlp'")
        sys.exit(1)
    
    try:
        import concurrent.futures
    except ImportError:
        print("Aviso: concurrent.futures não está disponível. Alguns recursos podem não funcionar.")
        
    app = PlaylistDownloader()
    app.run()