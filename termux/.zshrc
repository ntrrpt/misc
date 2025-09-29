export PATH=$HOME/cp:$HOME/bin:/usr/local/bin:$PATH:$HOME/.cargo/bin
export ZSH="$HOME/.oh-my-zsh"

plugins=(sudo extract fzf zsh-autosuggestions F-Sy-H git universalarchive)
ZSH_THEME="junkfood" #( 09/24/25@ 8:37PM )( u0_a246@localhost ):~

alias myip='curl http://ipecho.net/plain; echo'
alias a='tmux attach -t main || tmux new -s main'
alias cop="copyparty -c ~/cpp/cpp.conf"
alias fp="frpc -c ~/frpc.toml"
alias av='sudo avahi-daemon'

# https://ocv.me/dev/socks5server.py
sps() { UP=- sudo python3 ~/socks5server.py 0.0.0.0 43214; }

# port knocker knocking
# https://raw.githubusercontent.com/ntrrpt/misc/refs/heads/main/py/knock.py
knock() { nping --udp --count 1 --data-length 1 --dest-port $1 $PASTE_IP_HERE }
sq()
{
    for num in 1, 2, 3, 4, 5, 6, 7, 8, 9, 0; do
        knock $num
    done
}
sqq () {while true; do sq; sleep 10; done}

source $ZSH/oh-my-zsh.sh
