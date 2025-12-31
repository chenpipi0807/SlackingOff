const socket = io();

const terminalOutput = document.getElementById('output');
const terminalInput = document.getElementById('terminal-input');

terminalInput.focus();

socket.on('connect', () => {
    addOutput('已连接到服务器');
});

socket.on('message', (data) => {
    addOutput(data.data);
});

socket.on('output', (data) => {
    addOutput(data.data);
});

socket.on('clear', () => {
    terminalOutput.innerHTML = '';
});

terminalInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const command = terminalInput.value.trim();
        if (command) {
            addOutput(`PS C:\\MMP> ${command}`, 'command');
            socket.emit('command', { command: command });
            terminalInput.value = '';
        }
    }
});

function addOutput(text, type = 'output') {
    const line = document.createElement('div');
    line.className = `terminal-line ${type}`;
    line.textContent = text;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

document.addEventListener('click', (e) => {
    if (e.target.closest('.terminal')) {
        terminalInput.focus();
    }
});

addOutput('五子棋终端 v1.0');
addOutput('输入 @h 查看可用命令');
addOutput('');
