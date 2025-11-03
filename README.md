# YouConvert

![Badge](https://img.shields.io/badge/Status-Em%20Desenvolvimento-brightgreen)
![Badge](https://img.shields.io/badge/Python-3.6%2B-blue)

YouConvert é uma ferramenta de backend para download e conversão de mídia online. Permite baixar conteúdo de plataformas populares e converter para formatos de áudio e vídeo.

## Funcionalidades

- Download de vídeos e músicas de múltiplas plataformas
- Conversão para formatos MP3 e MP4
- Configuração de qualidade de áudio (128kbps até 320kbps)
- Seleção de resolução de vídeo (até 4K)
- Processamento simultâneo de múltiplos downloads
- Suporte a playlists completas
- Retentativas automáticas para downloads com falha

## Requisitos

- Python 3.6 ou superior
- Dependências: `yt-dlp`, `requests`
- ffmpeg para conversão de formatos

## Instalação do ffmpeg

O ffmpeg é essencial para o funcionamento do conversor. Baixe do [site oficial do ffmpeg](https://ffmpeg.org/download.html).

**Windows:**
- Baixe do [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (versão "essentials" recomendada)
- Extraia e adicione a pasta bin ao PATH do sistema

**macOS:**
```
brew install ffmpeg
```

**Linux:**
```
sudo apt update && sudo apt install ffmpeg
```

## Instalação do YouConvert

1. Instale as dependências:
```
pip install yt-dlp requests
```

2. Execute o script principal:
```
python app.py
```

## Considerações sobre o backend

- Utiliza multithreading para processamento paralelo
- Implementa gerenciamento de filas para controlar o fluxo de downloads
- Contém manipuladores de erro e sistema de retentativas
- Oferece API para monitoramento de progresso em tempo real
- Permite cancelamento de tarefas em andamento
- Implementa resolução de nomes de arquivos para evitar conflitos

## Nota Legal

Esta ferramenta deve ser usada apenas para baixar conteúdo com permissão adequada ou de domínio público. O desenvolvedor não se responsabiliza pelo uso indevido.

---

Desenvolvido com Python 🐍
