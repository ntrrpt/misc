export PATH=$HOME/.local/bin:$HOME/bin:/usr/local/bin:$PATH:$HOME/.cargo/bin
export ZSH="$HOME/.oh-my-zsh"

### Set variables
#################
HISTFILE=$HOME/.zhistory
HISTSIZE=100000000
SAVEHIST=100000000
LS_COLORS='rs=0:di=01;34:ln=01;36:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:su=37;41:sg=30;43:tw=30;42:ow=34;42:st=37;44:ex=01;32:'

plugins=(sudo extract fzf zsh-autosuggestions F-Sy-H git universalarchive poetry docker uv)
ZSH_THEME="junkfood" #( 09/24/25@ 8:37PM )( u0_a246@localhost ):~
source $ZSH/oh-my-zsh.sh
[ -f ~/.privrc ] && source ~/.privrc

### Set alias
#############
alias cls="clear"
alias ..="cd .."
alias cd..="cd .."
alias ll="ls -lisa --color=auto"
alias df="df -ahiT --total"
alias mkdir="mkdir -pv"
alias lsd='lazydocker'
alias rf="rm -rfv"
alias rm="rm -rfi"
alias userlist="cut -d: -f1 /etc/passwd"
alias ls="ls -CF --color=auto"
alias lsl="ls -lhFA | less"
alias free="free -mt"
alias du="du -ach | sort -h"
alias ps="ps auxf"
alias psgrep="ps aux | grep -v grep | grep -i -e VSZ -e"
alias wget="wget -c"
alias histg="history | grep"
alias logs="find /var/log -type f -exec file {} \; | grep 'text' | cut -d' ' -f1 | sed -e's/:$//g' | grep -v '[0-9]$' | xargs tail -f"
alias folders='find . -maxdepth 1 -type d -print0 | xargs -0 du -sk | sort -rn'
alias grep='grep --color=auto'
alias myip='curl http://ipecho.net/plain; echo'
alias pro='proxychains'
alias gal="gallery-dl -c ~/.gal.conf"
alias fp="ping 8.8.8.8"
#alias abaqus='LANG=en_US.utf8 /var/DassaultSystemes/SIMULIA/Commands/abaqus'
#export PATH="/var/DassaultSystemes/SIMULIA/Commands:$PATH"

# termux
alias a='tmux attach -t main || tmux new -s main'
alias cop="copyparty -c ~/cpp/cpp.conf"
alias frp="frpc -c ~/frpc.toml"
alias av='sudo avahi-daemon'

# eza
alias l="eza --color=always --group-directories-first"
alias ls='eza -l --color=always --group-directories-first --icons' # preferred listing
alias la='eza -al --color=always --group-directories-first --icons'  # all files and dirs
alias ll='eza -lisname -l --color=always --group-directories-first --icons'  # long format
alias lt='eza -aT --color=always --group-directories-first --icons' # tree listing
alias l.="eza -a | egrep '^\.'"                                     # show only dotfiles
alias lsl="eza -lF --color=always --group-directories-first --icons | less"
alias ld='eza -ld --color=always --group-directories-first --icons .*'
alias lS='eza -lFShssize --color=always --group-directories-first --icons'
alias lsf='eza -lh --color=never --group-directories-first | fzy'


# https://ocv.me/dev/socks5server.py
sps() { UP=- sudo python3 ~/socks5server.py 0.0.0.0 43214; }

ff()
{
    find . -type f -iname '*'"$*"'*' -ls ;
}

# get current host related info.
sysinfo()   
{
    echo -e "\n${BRed}System Informations:$NC " ; uname -a
    echo -e "\n${BRed}Online User:$NC " ; w -hs |
             cut -d " " -f1 | sort | uniq
    echo -e "\n${BRed}Date :$NC " ; date
    echo -e "\n${BRed}Server stats :$NC " ; uptime
    echo -e "\n${BRed}Memory stats :$NC " ; free
    echo -e "\n${BRed}Public IP Address :$NC " ; my_ip
    echo -e "\n${BRed}Open connections :$NC "; netstat -pan --inet;
    echo -e "\n${BRed}CPU info :$NC "; cat /proc/cpuinfo ;
    echo -e "\n"
}

my_ps() { ps $@ -u $USER -o pid,%cpu,%mem,bsdtime,command ; }

mcd () {
    mkdir -p $1
    cd $1
}

### Set/unset ZSH options
#########################
# setopt NOHUPexport USE_CCACHE=1
# setopt NOTIFY
# setopt NO_FLOW_CONTROL
setopt INC_APPEND_HISTORY SHARE_HISTORY
setopt APPEND_HISTORY
# setopt AUTO_LIST
# setopt AUTO_REMOVE_SLASH
# setopt AUTO_RESUME
unsetopt BG_NICE
#setopt CORRECT
setopt EXTENDED_HISTORY
# setopt HASH_CMDS
setopt MENUCOMPLETE

### Set/unset  shell options
############################
#setopt   notify globdots correct pushdtohome cdablevars autolist
#setopt   correctall autocd recexact longlistjobs
setopt   autoresume histignoredups pushdsilent
setopt   autopushd pushdminus extendedglob rcquotes mailwarning
unsetopt bgnice autoparamslash

### Autoload zsh modules when they are referenced
#################################################
autoload -U history-search-end
zmodload -a zsh/stat stat
zmodload -a zsh/zpty zpty
zmodload -a zsh/zprof zprof
#zmodload -ap zsh/mapfile mapfile
zle -N history-beginning-search-backward-end history-search-end
zle -N history-beginning-search-forward-end history-search-end

















