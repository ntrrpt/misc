```bash
pkg in ffmpeg uv tmux frp avahi zsh byobu wget git fzf

# ohmyzsh + plugins
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

git clone https://github.com/z-shell/F-Sy-H.git \
   ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/F-Sy-H
git clone https://github.com/zsh-users/zsh-autosuggestions \
   ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# uv
uv tool install 'copyparty[all]' --with "fusepy,pyvips[binary]"

uv tool install https://github.com/yt-dlp/yt-dlp.git -w 'pycryptodomex,pysocks,mutagen,requests,websockets,brotli,certifi,bgutil-ytdlp-pot-provider'

uv tool install git+https://github.com/mikf/gallery-dl --with 'yt-dlp,pysocks'

for pkg in streamlink scdl internetarchive; do
    uv tool install "$pkg"
done


```

