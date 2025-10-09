```bash
pkg in ffmpeg uv tmux frp zsh byobu wget git fzf rust vim micro croc

# omz
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# omz plugins
git clone https://github.com/z-shell/F-Sy-H.git \
   ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/F-Sy-H
git clone https://github.com/zsh-users/zsh-autosuggestions \
   ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# vim
git clone --depth=1 https://github.com/amix/vimrc.git ~/.vim_runtime && \
   sh ~/.vim_runtime/install_awesome_vimrc.sh

# cpp normal
uv tool install "copyparty[all]" --with "fusepy,pyvips[binary]"

# cpp termux
uv tool install copyparty --with "pyftpdlib,pillow,mutagen"

uv tool install https://github.com/yt-dlp/yt-dlp.git -w 'pycryptodomex,pysocks,mutagen,requests,websockets,brotli,certifi,bgutil-ytdlp-pot-provider'

uv tool install git+https://github.com/mikf/gallery-dl --with 'yt-dlp,pysocks'

for pkg in streamlink scdl internetarchive; do
    uv tool install "$pkg"
done


```





