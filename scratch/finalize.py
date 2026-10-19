import os

def main():
    with open('/Users/saadhan/Desktop/Qkd/scratch/out.tex', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Let's remove the manual title / author section and replace it with proper LaTeX
    # Find the abstract section
    abstract_idx = content.find('\\textbf{Abstract}')
    if abstract_idx != -1:
        # Extract the submission box and anything before abstract
        header_content = content[:abstract_idx]
        
        # We will wrap the text after \textbf{Abstract} until \textbf{Keywords } into \begin{abstract}
        rest = content[abstract_idx + len('\\textbf{Abstract}'):]
        
        # Find keywords
        kw_idx = rest.find('\\textbf{Keywords  }')
        if kw_idx != -1:
            abstract_text = rest[:kw_idx].strip()
            # Find the end of keywords
            # It's up to \section{Introduction}
            sec_idx = rest.find('\\section{Introduction}')
            keywords_text = rest[kw_idx + len('\\textbf{Keywords  }'):sec_idx].strip()
            
            body = rest[sec_idx:]
            
            preamble = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{caption}
\usepackage{hyperref}

\title{Aurora-QFlux: A Full-Stack Adaptive Quantum Key Distribution\\Simulation and Real-Time Visualization Framework}
\author{Adwitiya Mukhopadhyay \and Saadhan P \and Rashmitha S}
\date{May 2026}

\begin{document}

\maketitle

\begin{center}
\textit{Amrita School of Computing, Amrita Vishwa Vidyapeetham, Mysuru, Karnataka, India}\\
\texttt{adwitiya@my.amrita.edu $\cdot$ saadhan275@gmail.com $\cdot$ rashmithas588@gmail.com}\\
Corresponding author: Adwitiya Mukhopadhyay $\vert$ \texttt{adwitiya@my.amrita.edu}
\end{center}

\vspace{2em}

"""
            
            abstract_section = r"""\begin{abstract}
""" + abstract_text + r"""

\vspace{1em}
\noindent \textbf{Keywords:} """ + keywords_text + r"""
\end{abstract}

"""
            
            # The header content contains the submission box, let's keep it as an unnumbered section or just at the top
            # Actually, it's better to put the submission box before the title or right after abstract.
            # Let's just put it before the abstract
            
            submission_box = header_content.split('\n\n')[0] # The first block is the center table
            
            final_tex = preamble + submission_box + '\n\n' + abstract_section + body
            
            # Fix percentage signs by escaping them unless they are already escaped
            # But wait, there are percentage signs in the text like 50.1% which will comment out rest of the line in LaTeX
            final_tex = final_tex.replace('%', '\\%').replace('\\\\%', '\\%')
            
            with open('/Users/saadhan/Downloads/proper_converted_code.tex', 'w', encoding='utf-8') as out_f:
                out_f.write(final_tex)
            print("Successfully converted.")
        else:
            print("Keywords not found.")
    else:
        print("Abstract not found.")

if __name__ == '__main__':
    main()
