# uv tool install 'copyparty[all]' --with "fusepy,pyvips[binary]"

export PATH=$HOME/cp:$HOME/bin:/usr/local/bin:$PATH:$HOME/.cargo/bin
export ZSH="$HOME/.oh-my-zsh"
plugins=(sudo extract fzf zsh-autosuggestions F-Sy-H git universalarchive)
ZSH_THEME="junkfood"
source $ZSH/oh-my-zsh.sh

alias myip='curl http://ipecho.net/plain; echo'
alias a='tmux attach -t main || tmux new -s main'
alias cop="copyparty -c ~/cpp/copyp.conf"
alias fp="frpc -c ~/frpc.toml"
alias av='sudo avahi-daemon'

sps() { UP=- sudo python3 ~/socks5server.py 0.0.0.0 43214; }
knock() { nping --udp --count 1 --data-length 1 --dest-port $1 127.0.0.1 }
sq()
{
    for num in 1, 2, 3, 4, 5, 6, 7, 8, 9, 0; do
        knock $num
    done
}
sqq () {while true; do sq; sleep 10; done}

