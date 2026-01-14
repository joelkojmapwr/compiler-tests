import sys
import argparse
from lark import Lark, Transformer, Token

hasread = False
# --- GRAMATYKA LARK ---
LARK_GRAMMAR = r"""
    ?start: program_all

    program_all: procedures main

    procedures: (procedure)*
    procedure: "PROCEDURE" proc_head "IS" declarations "IN" commands "END" -> proc_decl_full
             | "PROCEDURE" proc_head "IS" "IN" commands "END"           -> proc_decl_empty

    main: "PROGRAM" "IS" declarations "IN" commands "END" -> main_full
        | "PROGRAM" "IS" "IN" commands "END"              -> main_empty

    commands: command+

    ?command: identifier ":=" expression ";"       -> assign
            | "IF" condition "THEN" commands "ELSE" commands "ENDIF" -> if_else
            | "IF" condition "THEN" commands "ENDIF"                 -> if_then
            | "WHILE" condition "DO" commands "ENDWHILE"             -> while_loop
            | "REPEAT" commands "UNTIL" condition ";"                -> repeat_until
            | "FOR" PIDENTIFIER "FROM" value "TO" value "DO" commands "ENDFOR"     -> for_to
            | "FOR" PIDENTIFIER "FROM" value "DOWNTO" value "DO" commands "ENDFOR" -> for_downto
            | proc_call ";"
            | "READ" identifier ";"                -> read_cmd
            | "WRITE" value ";"                    -> write_cmd

    proc_head: PIDENTIFIER "(" args_decl ")"
    proc_call: PIDENTIFIER "(" args ")"

    declarations: declaration ("," declaration)*
    ?declaration: PIDENTIFIER "[" NUM ":" NUM "]" -> decl_array
                | PIDENTIFIER                   -> decl_var

    args_decl: arg_decl ("," arg_decl)*
    arg_decl: type PIDENTIFIER -> get_arg_name

    type: "T" | "I" | "O" | 

    args: PIDENTIFIER ("," PIDENTIFIER)*

    ?expression: value           -> val_expr
               | value "+" value -> add
               | value "-" value -> sub
               | value "*" value -> mul
               | value "/" value -> div
               | value "%" value -> mod

    ?condition: value "=" value  -> eq
              | value "!=" value -> neq
              | value ">" value  -> gt
              | value "<" value  -> lt
              | value ">=" value -> geq
              | value "<=" value -> leq

    ?value: NUM         -> num_val
          | identifier  -> id_val

    ?identifier: PIDENTIFIER                     -> id_simple
               | PIDENTIFIER "[" PIDENTIFIER "]" -> id_array_var
               | PIDENTIFIER "[" NUM "]"         -> id_array_num

    PIDENTIFIER: /[_a-z]+/
    NUM: /[0-9]+/
    
    COMMENT: /#[^\n]*/
    %import common.WS
    %ignore COMMENT
    %ignore WS
"""

RUNTIME_HEADER = """
import sys

class SmartArray:
    def __init__(self, start, end):
        self.start = int(start)
        self.end = int(end)
        size = max(0, self.end - self.start + 1)
        self.data = [0] * size

    def _get_idx(self, i):
        return int(i) - self.start

    def get(self, i):
        idx = self._get_idx(i)
        return self.data[idx] if 0 <= idx < len(self.data) else 0

    def set(self, i, val):
        idx = self._get_idx(i)
        if 0 <= idx < len(self.data):
            self.data[idx] = val

def _sub(a, b): return max(0, a - b)
def _div(a, b): return a // b if b != 0 else 0
def _mod(a, b): return a % b if b != 0 else 0
"""

class ToPython(Transformer):
    def _indent(self, text):
        if not text: return ""
        return "\n".join("    " + line for line in text.splitlines())

    def PIDENTIFIER(self, token): return str(token)
    def NUM(self, token): return int(token)

    def program_all(self, items):
        return RUNTIME_HEADER + "\n" + "\n".join(items)

    def procedure(self, items): return items[0]
    def procedures(self, items): return "\n".join(items)

    def proc_decl_full(self, items):
        head, decls, cmds = items
        return f"\ndef {head}:\n{self._indent(decls)}\n{cmds}\n"

    def proc_decl_empty(self, items):
        head, cmds = items
        return f"\ndef {head}:\n{cmds}\n"

    def proc_head(self, items):
        name, args = items
        return f"{name}({args})"

    def args_decl(self, items):
        return ", ".join(items)

    def get_arg_name(self, items):
        # items to [type, name] lub [name]
        return items[-1]

    def main_full(self, items):
        decls, cmds = items
        return f"\ndef main():\n{self._indent(decls)}\n{cmds}\n\nif __name__ == '__main__':\n    main()"

    def main_empty(self, items):
        cmds = items[0]
        return f"\ndef main():\n{cmds}\n\nif __name__ == '__main__':\n    main()"

    def declarations(self, items):
        return "\n".join(items)

    def decl_var(self, item):
        return f"{item[0]} = [0]"

    def decl_array(self, items):
        name, start, end = items
        return f"{name} = SmartArray({start}, {end})"

    def commands(self, items):
        return "\n".join(self._indent(cmd) for cmd in items)

    def assign(self, items):
        target, expr = items
        if isinstance(target, tuple):
            return f"{target[0]}.set({target[1]}, {expr})"
        return f"{target}[0] = {expr}"

    def write_cmd(self, items):
        return f"print({items[0]})"

    def read_cmd(self, items):
        hasread = True
        target = items[0]
        if isinstance(target, tuple):
            return f"{target[0]}.set(int(input()), {target[1]})"
        return f"{target}[0] = int(input())"

    def if_else(self, items):
        cond, cmd_t, cmd_f = items
        return f"if {cond}:\n{cmd_t}\nelse:\n{cmd_f}"

    def if_then(self, items):
        cond, cmd_t = items
        return f"if {cond}:\n{cmd_t}"

    def while_loop(self, items):
        cond, cmds = items
        return f"while {cond}:\n{cmds}"

    def repeat_until(self, items):
        cmds, cond = items
        return f"while True:\n{cmds}\n    if {cond}: break"

    def for_to(self, items):
        var, start, end, cmds = items
        res = f"for __IND in range ({start},{end}+1):\n"
        res += f"    {var}= [__IND]\n"
        res += f"{cmds}\n"
        return res

    def for_downto(self, items):
        var, start, end, cmds = items
        res = f"for __IND in range ({start},{end}-1,-1):\n"
        res += f"    {var}= [__IND]\n"
        res += f"{cmds}\n"
        return res

    def proc_call(self, items):
        return f"{items[0]}({items[1]})"

    def args(self, items):
        return ", ".join(items)

    def val_expr(self, items): return items[0]
    def add(self, items): return f"({items[0]} + {items[1]})"
    def sub(self, items): return f"_sub({items[0]}, {items[1]})"
    def mul(self, items): return f"({items[0]} * {items[1]})"
    def div(self, items): return f"_div({items[0]}, {items[1]})"
    def mod(self, items): return f"_mod({items[0]}, {items[1]})"

    def num_val(self, items): return str(items[0])
    def id_val(self, items):
        target = items[0]
        if isinstance(target, tuple):
            return f"{target[0]}.get({target[1]})"
        return f"{target}[0]"

    def id_simple(self, items): return items[0]
    def id_array_num(self, items): return (items[0], items[1])
    def id_array_var(self, items): return (items[0], f"{items[1]}[0]")

    def eq(self, items): return f"{items[0]} == {items[1]}"
    def neq(self, items): return f"{items[0]} != {items[1]}"
    def gt(self, items): return f"{items[0]} > {items[1]}"
    def lt(self, items): return f"{items[0]} < {items[1]}"
    def geq(self, items): return f"{items[0]} >= {items[1]}"
    def leq(self, items): return f"{items[0]} <= {items[1]}"

def main():
    arg_p = argparse.ArgumentParser()
    arg_p.add_argument('input')
    args = arg_p.parse_args()

    with open(args.input, 'r') as f:
        source = f.read()

    lark_p = Lark(LARK_GRAMMAR, parser='lalr')
    tree = lark_p.parse(source)
    print(ToPython().transform(tree))

if __name__ == "__main__":
    main()
    sys.exit(1 if hasread else 0)
