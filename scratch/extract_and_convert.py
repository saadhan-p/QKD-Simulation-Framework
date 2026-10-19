import re
import sys

def main():
    tex_path = "/Users/saadhan/Downloads/proper_converted_code.tex"
    with open(tex_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc_start = content.find('// ── DOCUMENT')
    if doc_start == -1:
        print("Could not find DOCUMENT section")
        return
        
    # Find the main children array
    # It follows headers, footers etc.
    main_children_start = content.find('children:[', doc_start)
    # Actually wait, there are headers and footers with their own children:[.
    # Let's find the right one. The top level children array is indented with 4 spaces
    # It looks like:
    #     children:[
    # Let's search for it
    match = re.search(r'\n\s*children:\[\n(.*?)\n    \]\n  \}\]\n\}\);', content[doc_start:], re.DOTALL)
    if not match:
        print("Could not find main children array")
        return

    children_str = match.group(1)

    node_script = """
const r   = (t, o={}) => t;
const rb  = (t, o={}) => `\\\\textbf{${t}}`;
const ri  = (t, o={}) => `\\\\textit{${t}}`;
const rbi = (t, o={}) => `\\\\textbf{\\\\textit{${t}}}`;
const rs  = (t, o={}) => t;
const rsb = (t, o={}) => `\\\\textbf{${t}}`;
const rc  = (t, o={}) => `\\\\texttt{${t}}`;

const p = (c, o={}) => (Array.isArray(c)?c.join(''):c) + '\\n\\n';
const pC  = p;
const pL  = p;
const txt = (t, o={}) => t + '\\n\\n';
const gap = (n=1) => Array.from({length:n}, () => '\\n');

const sec  = t => `\\\\section{${t.replace(/^\\d+\\s+/, '')}}\\n`;
const sub  = t => `\\\\subsection{${t.replace(/^\\d+\\.\\d+\\s+/, '')}}\\n`;
const sub2 = t => `\\\\subsubsection{${t.replace(/^\\d+\\.\\d+\\.\\d+\\s+/, '')}}\\n`;

const tCap = t => `\\\\captionof{table}{${t.replace(/^Table \\d+\\s+/, '')}}\\n`;
const fCap = t => `\\\\captionof{figure}{${t.replace(/^Fig\\.\\s*\\d+\\s+/, '')}}\\n`;

const ref = t => `\\\\bibitem{ref${Math.random().toString(36).substring(7)}} ${t.replace(/^\\\[\\d+\\\]\\s+/, '')}\\n`;

let inBullets = false;
const bul = t => {
    return `\\\\item ${t}\\n`;
};

const figBox = t => `\\\\begin{figure}[hbt!]\\n\\\\centering\\n\\\\framebox{\\\\parbox{0.8\\\\textwidth}{\\\\centering ${t}}}\\n\\\\end{figure}\\n`;

const mkT = (headers, rows, cols, shade) => {
    let out = `\\\\begin{table}[hbt!]\\n\\\\centering\\n\\\\begin{tabular}{|${headers.map(()=>'c').join('|')}|}\\n\\\\hline\\n`;
    out += headers.map(rsb).join(' & ') + ' \\\\\\\\\\n\\\\hline\\n';
    rows.forEach(row => {
        out += row.map(rs).join(' & ') + ' \\\\\\\\\\n';
    });
    out += `\\\\hline\\n\\\\end{tabular}\\n\\\\end{table}\\n`;
    return out;
};

const infoBox = rows => {
    let out = `\\\\begin{center}\\n\\\\begin{tabular}{ll}\\n`;
    rows.forEach(([lbl, val]) => {
        out += `\\\\textbf{${lbl}} & ${val} \\\\\\\\\\n`;
    });
    out += `\\\\end{tabular}\\n\\\\end{center}\\n`;
    return out;
};

const Paragraph = class {
    constructor({children}) {
        this.children = children;
    }
    toString() {
        if (!this.children) return '';
        return this.children.map(c => c ? c.toString() : '').join('');
    }
};

const TextRun = class {
    constructor({children, text}) {
        if (text) this.val = text;
        else if (children) this.val = children.join('');
        else this.val = '';
    }
    toString() {
        if (this.val === PageNumber.CURRENT) return "1";
        return this.val;
    }
};

const AlignmentType = { JUSTIFIED: 1, CENTER: 2, RIGHT: 3, LEFT: 4 };
const BorderStyle = { SINGLE: 1, NONE: 0 };
const WidthType = { DXA: 1 };
const ShadingType = { CLEAR: 1 };
const LevelFormat = { BULLET: 1 };
const Header = class {};
const Footer = class {};


const PageNumber = { CURRENT: Symbol("CURRENT_PAGE") };

const children = [
""" + children_str + """
];

// Post-process to group bullets and references
let out = "";
let currentList = null;

for (let item of children) {
    if (!item) continue;
    if (Array.isArray(item)) {
        for (let sub of item) {
            out += sub;
        }
        continue;
    }
    let str = item.toString();
    
    // Check if it's a bullet
    if (str.startsWith('\\\\item') && !str.includes('\\\\bibitem')) {
        if (currentList !== 'itemize') {
            if (currentList) out += `\\\\end{${currentList}}\\n\\n`;
            out += `\\\\begin{itemize}\\n`;
            currentList = 'itemize';
        }
        out += str;
    } else if (str.startsWith('\\\\bibitem')) {
        if (currentList !== 'thebibliography') {
            if (currentList) out += `\\\\end{${currentList}}\\n\\n`;
            out += `\\\\begin{thebibliography}{99}\\n`;
            currentList = 'thebibliography';
        }
        out += str;
    } else {
        if (currentList) {
            out += `\\\\end{${currentList}}\\n\\n`;
            currentList = null;
        }
        out += str;
    }
}

if (currentList) {
    out += `\\\\end{${currentList}}\\n\\n`;
}

console.log(out);
"""
    with open("/Users/saadhan/Desktop/Qkd/scratch/generate.js", "w", encoding="utf-8") as f:
        f.write(node_script)

if __name__ == "__main__":
    main()
