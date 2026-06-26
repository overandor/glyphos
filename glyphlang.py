"""
GlyphLang — Glyphgramming Language Compiler
=============================================
A programming language where glyphs ARE the syntax.

  ⧉◇@L → H@L Æ R Æ λ⁻¹ = ◎ → $

Programs are written in glyph sequences. The compiler:
  1. Lexes glyphs into tokens
  2. Parses into AST
  3. Type-checks glyph bindings
  4. Transpiles to Python
  5. Executes and produces receipts

Example .glyph program:
  program SortSolver
    ◇@L → H@L
    H@L Æ R
    R Æ λ⁻¹
    λ⁻¹ = ◎
    ◎ → $
  end

Compile: python3 glyphlang.py compile sort.glyph
Run:     python3 glyphlang.py run sort.glyph
REPL:    python3 glyphlang.py repl
"""

import sys
import json
import time
import hashlib
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

# --- Glyph Token Types ---
TOKEN_TYPES = {
    "□": "FILE", "◇": "ARTIFACT", "⧉": "STATIONARY",
    "H": "HASH", "L": "LOCATION", "R": "RECEIPT",
    "λ": "FRICTION", "λ⁻¹": "TRANSFERABILITY",
    "T": "TIME", "Σ": "SHARD", "M": "MERKLE", "ZK": "ZK_PROOF",
    "Æ": "BIND", "→": "DERIVE", "=": "ASSERT",
    "Δ": "DELTA", "◎": "VERIFIED", "✕": "INVALID",
    "$": "VALUE", "Ω": "CANONICAL", "⟲": "LOOP",
    "@": "ANCHOR", ";": "SEPARATOR",
}

KEYWORDS = {"program", "end", "if", "else", "loop", "break", "emit", "claim", "prove", "pay"}


@dataclass
class GlyphToken:
    type: str
    value: str
    line: int
    col: int


@dataclass
class GlyphNode:
    node_type: str
    value: str = ""
    children: list = field(default_factory=list)
    line: int = 0

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "value": self.value, "children": [c.to_dict() for c in self.children], "line": self.line}


@dataclass
class GlyphProgram:
    name: str = ""
    statements: list = field(default_factory=list)
    source: str = ""
    hash: str = ""
    compiled_at: float = 0.0

    def to_dict(self) -> dict:
        return {"name": self.name, "statements": [s.to_dict() for s in self.statements], "hash": self.hash, "compiled_at": self.compiled_at}


class GlyphLexer:
    """Tokenizes .glyph source into glyph tokens."""

    def lex(self, source: str) -> list[GlyphToken]:
        tokens = []
        lines = source.split("\n")
        for line_num, line in enumerate(lines, 1):
            col = 0
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check for keywords (only first word on line)
            words = stripped.split()
            if words and words[0] in KEYWORDS and words[0] != "end":
                tokens.append(GlyphToken("KEYWORD", words[0], line_num, col))
                col += len(words[0]) + 1
                # Rest of line: tokenize as glyphs
                rest = stripped[len(words[0]):]
                i = 0
                while i < len(rest):
                    ch = rest[i]
                    if ch in " \t":
                        i += 1
                        col += 1
                        continue
                    matched = False
                    for glyph in sorted(TOKEN_TYPES.keys(), key=len, reverse=True):
                        if rest[i:i+len(glyph)] == glyph:
                            tokens.append(GlyphToken(TOKEN_TYPES[glyph], glyph, line_num, col))
                            i += len(glyph)
                            col += len(glyph)
                            matched = True
                            break
                    if not matched:
                        if ch.isalpha() or ch == "_":
                            j = i
                            while j < len(rest) and (rest[j].isalnum() or rest[j] == "_"):
                                j += 1
                            tokens.append(GlyphToken("IDENT", rest[i:j], line_num, col))
                            col += j - i
                            i = j
                        else:
                            i += 1
                            col += 1
                continue

            # Check for standalone end
            if stripped == "end":
                tokens.append(GlyphToken("KEYWORD", "end", line_num, col))
                continue

            # Tokenize glyph sequence
            i = 0
            while i < len(line):
                ch = line[i]
                if ch in " \t":
                    i += 1
                    col += 1
                    continue

                # Multi-char glyphs
                matched = False
                for glyph in sorted(TOKEN_TYPES.keys(), key=len, reverse=True):
                    if line[i:i+len(glyph)] == glyph:
                        tokens.append(GlyphToken(TOKEN_TYPES[glyph], glyph, line_num, col))
                        i += len(glyph)
                        col += len(glyph)
                        matched = True
                        break

                if not matched:
                    if ch.isalpha() or ch == "_":
                        j = i
                        while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                            j += 1
                        word = line[i:j]
                        if word in KEYWORDS:
                            tokens.append(GlyphToken("KEYWORD", word, line_num, col))
                        else:
                            tokens.append(GlyphToken("IDENT", word, line_num, col))
                        col += j - i
                        i = j
                    elif ch.isdigit():
                        j = i
                        while j < len(line) and (line[j].isdigit() or line[j] == "."):
                            j += 1
                        tokens.append(GlyphToken("NUMBER", line[i:j], line_num, col))
                        col += j - i
                        i = j
                    else:
                        tokens.append(GlyphToken("UNKNOWN", ch, line_num, col))
                        i += 1
                        col += 1

        return tokens


class GlyphParser:
    """Parses glyph tokens into AST."""

    def __init__(self):
        self.tokens: list[GlyphToken] = []
        self.pos = 0

    def parse(self, tokens: list[GlyphToken]) -> GlyphProgram:
        self.tokens = tokens
        self.pos = 0
        prog = GlyphProgram()

        # Expect: program <name>
        if self.peek() and self.peek().type == "KEYWORD" and self.peek().value == "program":
            self.advance()
            # Skip any IDENT or KEYWORD that is the program name
            if self.peek() and self.peek().type in ("IDENT", "KEYWORD") and self.peek().value != "end":
                prog.name = self.advance().value

        # Parse statements until end
        while self.pos < len(self.tokens):
            tok = self.peek()
            if tok is None:
                break
            if tok.type == "KEYWORD" and tok.value == "end":
                break
            stmt = self.parse_statement()
            if stmt:
                prog.statements.append(stmt)

        return prog

    def peek(self, offset=0) -> Optional[GlyphToken]:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def advance(self) -> Optional[GlyphToken]:
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def parse_statement(self) -> Optional[GlyphNode]:
        tok = self.peek()
        if tok is None:
            return None

        # Keyword statements
        if tok.type == "KEYWORD":
            if tok.value == "if":
                return self.parse_if()
            elif tok.value == "loop":
                return self.parse_loop()
            elif tok.value == "emit":
                self.advance()
                expr = self.parse_glyph_chain()
                return GlyphNode("emit", "emit", [expr] if expr else [], tok.line)
            elif tok.value == "claim":
                self.advance()
                expr = self.parse_glyph_chain()
                return GlyphNode("claim", "claim", [expr] if expr else [], tok.line)
            elif tok.value == "prove":
                self.advance()
                expr = self.parse_glyph_chain()
                return GlyphNode("prove", "prove", [expr] if expr else [], tok.line)
            elif tok.value == "pay":
                self.advance()
                expr = self.parse_glyph_chain()
                return GlyphNode("pay", "pay", [expr] if expr else [], tok.line)
            else:
                self.advance()
                return GlyphNode("keyword", tok.value, [], tok.line)

        # Glyph chain: ◇@L → H@L Æ R Æ λ⁻¹ = ◎ → $
        return self.parse_glyph_chain()

    def parse_glyph_chain(self) -> Optional[GlyphNode]:
        left = self.parse_glyph_expr()
        if left is None:
            return None

        chain = [left]
        while self.peek() and self.peek().type in ("BIND", "DERIVE", "ASSERT", "SEPARATOR"):
            op = self.advance()
            right = self.parse_glyph_expr()
            if right:
                chain.append(GlyphNode("operator", op.value, [right], op.line))

        if len(chain) == 1:
            return chain[0]
        return GlyphNode("chain", "chain", chain, left.line)

    def parse_glyph_expr(self) -> Optional[GlyphNode]:
        tok = self.peek()
        if tok is None:
            return None

        # Anchor: ◇@L
        if tok.type in ("FILE", "ARTIFACT", "STATIONARY", "HASH", "RECEIPT"):
            node = GlyphNode("glyph", tok.value, [], tok.line)
            self.advance()
            if self.peek() and self.peek().type == "ANCHOR":
                self.advance()
                if self.peek() and self.peek().type in ("LOCATION", "TIME"):
                    anchored = self.advance()
                    node.children.append(GlyphNode("anchor", anchored.value, [], tok.line))
            return node

        if tok.type in ("FRICTION", "TRANSFERABILITY", "DELTA", "VERIFIED",
                        "INVALID", "VALUE", "CANONICAL", "SHARD", "MERKLE",
                        "ZK_PROOF", "TIME", "LOOP", "RECEIPT", "HASH"):
            self.advance()
            return GlyphNode("glyph", tok.value, [], tok.line)

        if tok.type in ("IDENT", "NUMBER"):
            self.advance()
            return GlyphNode("literal", tok.value, [], tok.line)

        return None

    def parse_if(self) -> GlyphNode:
        line = self.advance().line  # if
        cond = self.parse_glyph_chain()
        body = []
        while self.peek() and not (self.peek().type == "KEYWORD" and self.peek().value in ("else", "end")):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
        else_body = []
        if self.peek() and self.peek().type == "KEYWORD" and self.peek().value == "else":
            self.advance()
            while self.peek() and not (self.peek().type == "KEYWORD" and self.peek().value == "end"):
                stmt = self.parse_statement()
                if stmt:
                    else_body.append(stmt)
        if self.peek() and self.peek().type == "KEYWORD" and self.peek().value == "end":
            self.advance()
        return GlyphNode("if", "if", [cond] + body, line)

    def parse_loop(self) -> GlyphNode:
        line = self.advance().line  # loop
        body = []
        while self.peek() and not (self.peek().type == "KEYWORD" and self.peek().value == "end"):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
        if self.peek() and self.peek().type == "KEYWORD" and self.peek().value == "end":
            self.advance()
        return GlyphNode("loop", "loop", body, line)


class GlyphCompiler:
    """Compiles .glyph programs to multiple target languages.

    Glyphs superimpose semantic meaning onto any known language.
    Write once in glyph prose, compile to C++, Swift, C, Obj-C, Rust, Python.

    Semantic map:
      ◇@L → H@L    =  declare artifact, compute hash
      H@L Æ R       =  bind hash to receipt struct
      R Æ λ⁻¹       =  receipt becomes transferable
      λ⁻¹ = ◎       =  assert verified
      ◎ → $         =  verified becomes payable
      emit X        =  return / print X
      claim X       =  create claim object
      prove X       =  run verification
      pay X         =  release payment
    """

    TARGETS = ["cpp", "swift", "c", "objc", "rust", "python"]

    def __init__(self):
        self.lexer = GlyphLexer()
        self.parser = GlyphParser()

    def compile(self, source: str, targets: list[str] = None) -> dict:
        tokens = self.lexer.lex(source)
        program = self.parser.parse(tokens)
        program.source = source
        program.hash = hashlib.sha256(source.encode()).hexdigest()[:16]
        program.compiled_at = time.time()

        targets = targets or self.TARGETS
        errors = self.type_check(program)

        # Transpile to all targets
        outputs = {}
        for target in targets:
            outputs[target] = self.transpile(program, target)

        return {
            "program": program.to_dict(),
            "outputs": outputs,
            "token_count": len(tokens),
            "statement_count": len(program.statements),
            "errors": errors,
            "hash": program.hash,
            "compiled_at": program.compiled_at,
            "status": "compiled" if not errors else "errors",
            "targets": targets,
        }

    def transpile(self, program: GlyphProgram, target: str = "python") -> str:
        dispatch = {
            "python": self._to_python,
            "cpp": self._to_cpp,
            "swift": self._to_swift,
            "c": self._to_c,
            "objc": self._to_objc,
            "rust": self._to_rust,
        }
        fn = dispatch.get(target, self._to_python)
        return fn(program)

    # --- Python target ---
    def _to_python(self, program: GlyphProgram) -> str:
        lines = [
            f"# Auto-generated from .glyph: {program.name}",
            f"# Hash: {program.hash}",
            f"import time, hashlib, json",
            f"",
            f"class {program.name or 'GlyphProgram'}:",
            f"    def __init__(self):",
            f"        self.receipts = []",
            f"        self.state = {{}}",
            f"",
            f"    def run(self):",
        ]
        for stmt in program.statements:
            py = self._py_node(stmt, 8)
            if py:
                lines.append(py)
        lines.append(f"        return self.receipts")
        return "\n".join(lines)

    def _py_node(self, node: GlyphNode, indent: int) -> str:
        pad = " " * indent
        if node.node_type == "chain":
            parts = []
            for child in node.children:
                if child.node_type == "operator" and child.children:
                    parts.append(child.value)
                    parts.append(child.children[0].value)
                else:
                    parts.append(child.value)
            chain_str = " ".join(parts)
            return f"{pad}self.receipts.append({{'type': 'chain', 'glyph': {repr(chain_str)}, 'ts': time.time()}})"
        elif node.node_type == "glyph":
            return f"{pad}self.state[{repr(node.value)}] = True"
        elif node.node_type == "emit":
            return f'{pad}self.receipts.append({{"type": "emit", "ts": time.time()}})'
        elif node.node_type == "claim":
            return f'{pad}self.receipts.append({{"type": "claim", "ts": time.time()}})'
        elif node.node_type == "prove":
            return f'{pad}self.receipts.append({{"type": "prove", "ts": time.time()}})'
        elif node.node_type == "pay":
            return f'{pad}self.receipts.append({{"type": "pay", "ts": time.time()}})'
        elif node.node_type == "if":
            lines = [f'{pad}if True:  # {node.value}']
            for child in node.children[1:]:
                py = self._py_node(child, indent + 4)
                if py: lines.append(py)
            return "\n".join(lines)
        elif node.node_type == "loop":
            lines = [f'{pad}for _ in range(1):  # loop']
            for child in node.children:
                py = self._py_node(child, indent + 4)
                if py: lines.append(py)
            return "\n".join(lines)
        return f'{pad}pass  # {node.node_type}: {node.value}'

    # --- C++ target ---
    def _to_cpp(self, program: GlyphProgram) -> str:
        name = program.name or "GlyphProgram"
        lines = [
            f"// Auto-generated from .glyph: {name}",
            f"// Hash: {program.hash}",
            f"// Glyphs superimposed onto C++",
            f"#include <iostream>",
            f"#include <vector>",
            f"#include <string>",
            f"#include <chrono>",
            f"#include <openssl/sha.h>",
            f"",
            f"struct Receipt {{",
            f"    std::string type;",
            f"    std::string glyph;",
            f"    double timestamp;",
            f"}};",
            f"",
            f"class {name} {{",
            f"public:",
            f"    std::vector<Receipt> receipts;",
            f"    ",
            f"    void run() {{",
        ]
        for stmt in program.statements:
            cpp = self._cpp_node(stmt, 8)
            if cpp: lines.append(cpp)
        lines.append(f"    }}")
        lines.append(f"}};")
        lines.append(f"")
        lines.append(f"int main() {{")
        lines.append(f"    {name} prog;")
        lines.append(f"    prog.run();")
        lines.append(f"    for (const auto& r : prog.receipts)")
        lines.append(f'        std::cout << r.type << ": " << r.glyph << std::endl;')
        lines.append(f"    return 0;")
        lines.append(f"}}")
        return "\n".join(lines)

    def _cpp_node(self, node: GlyphNode, indent: int) -> str:
        pad = " " * indent
        if node.node_type == "chain":
            parts = []
            for child in node.children:
                if child.node_type == "operator" and child.children:
                    parts.append(child.value)
                    parts.append(child.children[0].value)
                else:
                    parts.append(child.value)
            chain_str = " ".join(parts)
            return f'{pad}receipts.push_back({{"chain", "{chain_str}", now()}});'
        elif node.node_type == "glyph":
            return f'{pad}// glyph: {node.value}'
        elif node.node_type == "emit":
            return f'{pad}receipts.push_back({{"emit", "", now()}});'
        elif node.node_type == "claim":
            return f'{pad}receipts.push_back({{"claim", "", now()}});'
        elif node.node_type == "prove":
            return f'{pad}receipts.push_back({{"prove", "", now()}});'
        elif node.node_type == "pay":
            return f'{pad}receipts.push_back({{"pay", "", now()}});'
        elif node.node_type == "if":
            lines = [f'{pad}if (true) {{ // {node.value}']
            for child in node.children[1:]:
                cpp = self._cpp_node(child, indent + 4)
                if cpp: lines.append(cpp)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        elif node.node_type == "loop":
            lines = [f'{pad}for (int _i = 0; _i < 1; _i++) {{ // loop']
            for child in node.children:
                cpp = self._cpp_node(child, indent + 4)
                if cpp: lines.append(cpp)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        return f'{pad}// {node.node_type}: {node.value}'

    # --- Swift target ---
    def _to_swift(self, program: GlyphProgram) -> str:
        name = program.name or "GlyphProgram"
        lines = [
            f"// Auto-generated from .glyph: {name}",
            f"// Hash: {program.hash}",
            f"// Glyphs superimposed onto Swift",
            f"import Foundation",
            f"import CryptoKit",
            f"",
            f"struct Receipt: Codable {{",
            f"    var type: String",
            f"    var glyph: String",
            f"    var timestamp: Double",
            f"}}",
            f"",
            f"class {name} {{",
            f"    var receipts: [Receipt] = []",
            f"    ",
            f"    func run() {{",
        ]
        for stmt in program.statements:
            sw = self._swift_node(stmt, 8)
            if sw: lines.append(sw)
        lines.append(f"    }}")
        lines.append(f"}}")
        lines.append(f"")
        lines.append(f'let prog = {name}()')
        lines.append(f"prog.run()")
        lines.append(f'for r in prog.receipts {{ print("\\(r.type): \\(r.glyph)") }}')
        return "\n".join(lines)

    def _swift_node(self, node: GlyphNode, indent: int) -> str:
        pad = " " * indent
        if node.node_type == "chain":
            parts = []
            for child in node.children:
                if child.node_type == "operator" and child.children:
                    parts.append(child.value)
                    parts.append(child.children[0].value)
                else:
                    parts.append(child.value)
            chain_str = " ".join(parts)
            return f'receipts.append(Receipt(type: "chain", glyph: "{chain_str}", timestamp: Date().timeIntervalSince1970))'
        elif node.node_type == "glyph":
            return f'{pad}// glyph: {node.value}'
        elif node.node_type == "emit":
            return f'receipts.append(Receipt(type: "emit", glyph: "", timestamp: Date().timeIntervalSince1970))'
        elif node.node_type == "claim":
            return f'receipts.append(Receipt(type: "claim", glyph: "", timestamp: Date().timeIntervalSince1970))'
        elif node.node_type == "prove":
            return f'receipts.append(Receipt(type: "prove", glyph: "", timestamp: Date().timeIntervalSince1970))'
        elif node.node_type == "pay":
            return f'receipts.append(Receipt(type: "pay", glyph: "", timestamp: Date().timeIntervalSince1970))'
        elif node.node_type == "if":
            lines = [f'{pad}if true {{ // {node.value}']
            for child in node.children[1:]:
                sw = self._swift_node(child, indent + 4)
                if sw: lines.append(sw)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        elif node.node_type == "loop":
            lines = [f'{pad}for _ in 0..<1 {{ // loop']
            for child in node.children:
                sw = self._swift_node(child, indent + 4)
                if sw: lines.append(sw)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        return f'{pad}// {node.node_type}: {node.value}'

    # --- C target ---
    def _to_c(self, program: GlyphProgram) -> str:
        name = program.name or "glyph_program"
        lines = [
            f"/* Auto-generated from .glyph: {name} */",
            f"/* Hash: {program.hash} */",
            f"/* Glyphs superimposed onto C */",
            f"#include <stdio.h>",
            f"#include <stdlib.h>",
            f"#include <string.h>",
            f"#include <time.h>",
            f"",
            f"typedef struct {{",
            f"    char type[32];",
            f"    char glyph[256];",
            f"    double timestamp;",
            f"}} Receipt;",
            f"",
            f"static Receipt receipts[1024];",
            f"static int receipt_count = 0;",
            f"",
            f"static double now_sec() {{",
            f"    struct timespec ts;",
            f"    clock_gettime(CLOCK_REALTIME, &ts);",
            f"    return ts.tv_sec + ts.tv_nsec / 1e9;",
            f"}}",
            f"",
            f"static void add_receipt(const char* type, const char* glyph) {{",
            f"    if (receipt_count < 1024) {{",
            f"        strncpy(receipts[receipt_count].type, type, 31);",
            f"        strncpy(receipts[receipt_count].glyph, glyph, 255);",
            f"        receipts[receipt_count].timestamp = now_sec();",
            f"        receipt_count++;",
            f"    }}",
            f"}}",
            f"",
            f"void {name}_run() {{",
        ]
        for stmt in program.statements:
            c = self._c_node(stmt, 4)
            if c: lines.append(c)
        lines.append(f"}}")
        lines.append(f"")
        lines.append(f"int main() {{")
        lines.append(f"    {name}_run();")
        lines.append(f'    for (int i = 0; i < receipt_count; i++)')
        lines.append(f'        printf("%s: %s\\n", receipts[i].type, receipts[i].glyph);')
        lines.append(f"    return 0;")
        lines.append(f"}}")
        return "\n".join(lines)

    def _c_node(self, node: GlyphNode, indent: int) -> str:
        pad = " " * indent
        if node.node_type == "chain":
            parts = []
            for child in node.children:
                if child.node_type == "operator" and child.children:
                    parts.append(child.value)
                    parts.append(child.children[0].value)
                else:
                    parts.append(child.value)
            chain_str = " ".join(parts)
            return f'{pad}add_receipt("chain", "{chain_str}");'
        elif node.node_type == "glyph":
            return f'{pad}/* glyph: {node.value} */'
        elif node.node_type == "emit":
            return f'{pad}add_receipt("emit", "");'
        elif node.node_type == "claim":
            return f'{pad}add_receipt("claim", "");'
        elif node.node_type == "prove":
            return f'{pad}add_receipt("prove", "");'
        elif node.node_type == "pay":
            return f'{pad}add_receipt("pay", "");'
        elif node.node_type == "if":
            lines = [f'{pad}if (1) {{ /* {node.value} */']
            for child in node.children[1:]:
                c = self._c_node(child, indent + 4)
                if c: lines.append(c)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        elif node.node_type == "loop":
            lines = [f'{pad}for (int _i = 0; _i < 1; _i++) {{ /* loop */']
            for child in node.children:
                c = self._c_node(child, indent + 4)
                if c: lines.append(c)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        return f'{pad}/* {node.node_type}: {node.value} */'

    # --- Objective-C target ---
    def _to_objc(self, program: GlyphProgram) -> str:
        name = program.name or "GlyphProgram"
        lines = [
            f"// Auto-generated from .glyph: {name}",
            f"// Hash: {program.hash}",
            f"// Glyphs superimposed onto Objective-C",
            f"#import <Foundation/Foundation.h>",
            f"#import <CommonCrypto/CommonDigest.h>",
            f"",
            f"@interface Receipt : NSObject",
            f"@property (nonatomic, strong) NSString *type;",
            f"@property (nonatomic, strong) NSString *glyph;",
            f"@property (nonatomic, assign) NSTimeInterval timestamp;",
            f"@end",
            f"@implementation Receipt",
            f"@end",
            f"",
            f"@interface {name} : NSObject",
            f"@property (nonatomic, strong) NSMutableArray<Receipt *> *receipts;",
            f"- (void)run;",
            f"@end",
            f"",
            f"@implementation {name}",
            f"",
            f"- (instancetype)init {{",
            f"    self = [super init];",
            f"    if (self) {{",
            f"        _receipts = [NSMutableArray array];",
            f"    }}",
            f"    return self;",
            f"}}",
            f"",
            f"- (void)run {{",
        ]
        for stmt in program.statements:
            objc = self._objc_node(stmt, 8)
            if objc: lines.append(objc)
        lines.append(f"}}")
        lines.append(f"@end")
        lines.append(f"")
        lines.append(f"int main() {{")
        lines.append(f"    @autoreleasepool {{")
        lines.append(f"        {name} *prog = [[{name} alloc] init];")
        lines.append(f"        [prog run];")
        lines.append(f"        for (Receipt *r in prog.receipts)")
        lines.append(f'            NSLog(@"%@: %@", r.type, r.glyph);')
        lines.append(f"    }}")
        lines.append(f"    return 0;")
        lines.append(f"}}")
        return "\n".join(lines)

    def _objc_node(self, node: GlyphNode, indent: int) -> str:
        pad = " " * indent
        if node.node_type == "chain":
            parts = []
            for child in node.children:
                if child.node_type == "operator" and child.children:
                    parts.append(child.value)
                    parts.append(child.children[0].value)
                else:
                    parts.append(child.value)
            chain_str = " ".join(parts)
            return (f'{pad}Receipt *r = [[Receipt alloc] init];\n'
                    f'{pad}r.type = @"chain";\n'
                    f'{pad}r.glyph = @"{chain_str}";\n'
                    f'{pad}r.timestamp = [[NSDate date] timeIntervalSince1970];\n'
                    f'{pad}[self.receipts addObject:r];')
        elif node.node_type == "glyph":
            return f'{pad}// glyph: {node.value}'
        elif node.node_type == "emit":
            return (f'{pad}Receipt *r = [[Receipt alloc] init];\n'
                    f'{pad}r.type = @"emit";\n'
                    f'{pad}r.timestamp = [[NSDate date] timeIntervalSince1970];\n'
                    f'{pad}[self.receipts addObject:r];')
        elif node.node_type == "claim":
            return (f'{pad}Receipt *r = [[Receipt alloc] init];\n'
                    f'{pad}r.type = @"claim";\n'
                    f'{pad}r.timestamp = [[NSDate date] timeIntervalSince1970];\n'
                    f'{pad}[self.receipts addObject:r];')
        elif node.node_type == "prove":
            return (f'{pad}Receipt *r = [[Receipt alloc] init];\n'
                    f'{pad}r.type = @"prove";\n'
                    f'{pad}r.timestamp = [[NSDate date] timeIntervalSince1970];\n'
                    f'{pad}[self.receipts addObject:r];')
        elif node.node_type == "pay":
            return (f'{pad}Receipt *r = [[Receipt alloc] init];\n'
                    f'{pad}r.type = @"pay";\n'
                    f'{pad}r.timestamp = [[NSDate date] timeIntervalSince1970];\n'
                    f'{pad}[self.receipts addObject:r];')
        elif node.node_type == "if":
            lines = [f'{pad}if (YES) {{ // {node.value}']
            for child in node.children[1:]:
                objc = self._objc_node(child, indent + 4)
                if objc: lines.append(objc)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        elif node.node_type == "loop":
            lines = [f'{pad}for (int _i = 0; _i < 1; _i++) {{ // loop']
            for child in node.children:
                objc = self._objc_node(child, indent + 4)
                if objc: lines.append(objc)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        return f'{pad}// {node.node_type}: {node.value}'

    # --- Rust target ---
    def _to_rust(self, program: GlyphProgram) -> str:
        name = program.name or "GlyphProgram"
        # Rust uses snake_case for module names
        rust_name = name
        lines = [
            f"// Auto-generated from .glyph: {name}",
            f"// Hash: {program.hash}",
            f"// Glyphs superimposed onto Rust",
            f"use std::time::{{SystemTime, UNIX_EPOCH}};",
            f"",
            f"#[derive(Debug, Clone)]",
            f"struct Receipt {{",
            f"    r_type: String,",
            f"    glyph: String,",
            f"    timestamp: f64,",
            f"}}",
            f"",
            f"fn now_sec() -> f64 {{",
            f"    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs_f64()",
            f"}}",
            f"",
            f"struct {rust_name} {{",
            f"    receipts: Vec<Receipt>,",
            f"}}",
            f"",
            f"impl {rust_name} {{",
            f"    fn new() -> Self {{",
            f"        {rust_name} {{ receipts: Vec::new() }}",
            f"    }}",
            f"",
            f"    fn run(&mut self) {{",
        ]
        for stmt in program.statements:
            rs = self._rust_node(stmt, 12)
            if rs: lines.append(rs)
        lines.append(f"    }}")
        lines.append(f"}}")
        lines.append(f"")
        lines.append(f"fn main() {{")
        lines.append(f"    let mut prog = {rust_name}::new();")
        lines.append(f"    prog.run();")
        lines.append(f"    for r in &prog.receipts {{")
        lines.append(f'        println!("{{}}: {{}}", r.r_type, r.glyph);')
        lines.append(f"    }}")
        lines.append(f"}}")
        return "\n".join(lines)

    def _rust_node(self, node: GlyphNode, indent: int) -> str:
        pad = " " * indent
        if node.node_type == "chain":
            parts = []
            for child in node.children:
                if child.node_type == "operator" and child.children:
                    parts.append(child.value)
                    parts.append(child.children[0].value)
                else:
                    parts.append(child.value)
            chain_str = " ".join(parts)
            return f'{pad}self.receipts.push(Receipt {{ r_type: "chain".into(), glyph: "{chain_str}".into(), timestamp: now_sec() }});'
        elif node.node_type == "glyph":
            return f'{pad}// glyph: {node.value}'
        elif node.node_type == "emit":
            return f'{pad}self.receipts.push(Receipt {{ r_type: "emit".into(), glyph: "".into(), timestamp: now_sec() }});'
        elif node.node_type == "claim":
            return f'{pad}self.receipts.push(Receipt {{ r_type: "claim".into(), glyph: "".into(), timestamp: now_sec() }});'
        elif node.node_type == "prove":
            return f'{pad}self.receipts.push(Receipt {{ r_type: "prove".into(), glyph: "".into(), timestamp: now_sec() }});'
        elif node.node_type == "pay":
            return f'{pad}self.receipts.push(Receipt {{ r_type: "pay".into(), glyph: "".into(), timestamp: now_sec() }});'
        elif node.node_type == "if":
            lines = [f'{pad}if true {{ // {node.value}']
            for child in node.children[1:]:
                rs = self._rust_node(child, indent + 4)
                if rs: lines.append(rs)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        elif node.node_type == "loop":
            lines = [f'{pad}for _ in 0..1 {{ // loop']
            for child in node.children:
                rs = self._rust_node(child, indent + 4)
                if rs: lines.append(rs)
            lines.append(f'{pad}}}')
            return "\n".join(lines)
        return f'{pad}// {node.node_type}: {node.value}'

    def type_check(self, program: GlyphProgram) -> list[str]:
        errors = []
        for i, stmt in enumerate(program.statements):
            if stmt.node_type == "chain":
                all_vals = self._collect_values(stmt)
                has_verified = "◎" in all_vals or "✕" in all_vals
                has_assert = "=" in all_vals
                if has_assert and not has_verified:
                    errors.append(f"Statement {i+1}: assertion '=' requires ◎ or ✕")
        return errors

    def _collect_values(self, node: GlyphNode) -> list[str]:
        vals = [node.value]
        for child in node.children:
            vals.extend(self._collect_values(child))
        return vals

    def execute(self, source: str) -> dict:
        result = self.compile(source, targets=["python"])
        if result["errors"]:
            result["status"] = "error"
            result["receipts"] = []
            result["receipt_count"] = 0
            return result

        # Execute the transpiled Python
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(result["outputs"]["python"])
            f.flush()
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("glyph_module", f.name)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                cls = getattr(mod, result["program"]["name"] or "GlyphProgram")
                instance = cls()
                receipts = instance.run()
                result["receipts"] = receipts
                result["status"] = "executed"
                result["receipt_count"] = len(receipts)
            except Exception as e:
                result["status"] = "runtime_error"
                result["error"] = str(e)
            finally:
                os.unlink(f.name)

        return result


# --- InkStream: Continuous Pen-Continuity Glyph Engine ---
# Stores 234,322+ unique glyphs, generates 34/min continuously.
# Like a WebSocket subscription but with ink — pen never leaves screen.

class InkStream:
    """Continuous glyph generation engine.

    Pen-continuity: glyphs flow as continuous ink, never lifting the pen.
    Each glyph is chained to the previous via SHA-256.
    Target: 234,322 unique glyphs, 34 new glyphs/minute.
    """

    def __init__(self, target_count: int = 234322, rate_per_min: int = 34):
        self.target_count = target_count
        self.rate_per_min = rate_per_min
        self.glyphs: list[dict] = []
        self.glyph_index: dict[str, int] = {}
        self.ink_chain: str = ""
        self.operators = list(TOKEN_TYPES.keys())
        self.start_time = time.time()
        self.total_generated = 0
        self.duplicates_rejected = 0

        # Seed with master glyph
        self._emit_glyph("⧉◇@L → H@L Æ R Æ λ⁻¹ = ◎ → $", "seed")

    def _emit_glyph(self, symbol: str, source: str = "generated") -> dict:
        """Emit a single glyph, chained to previous via ink hash."""
        if symbol in self.glyph_index:
            self.duplicates_rejected += 1
            return None

        ink_hash = hashlib.sha256((self.ink_chain + symbol).encode()).hexdigest()[:16]
        self.ink_chain = ink_hash

        glyph = {
            "id": f"ink_{self.total_generated:06d}",
            "symbol": symbol,
            "ink_hash": ink_hash,
            "prev_ink": self.glyphs[-1]["ink_hash"] if self.glyphs else "",
            "source": source,
            "generated_at": time.time() - self.start_time,
            "index": self.total_generated,
        }
        self.glyphs.append(glyph)
        self.glyph_index[symbol] = self.total_generated
        self.total_generated += 1
        return glyph

    def _generate_symbol(self) -> str:
        """Generate a unique glyph symbol by combining operators."""
        import random as _r
        patterns = [
            lambda: f"{_r.choice(self.operators)}@{_r.choice(['L','T'])}",
            lambda: f"{_r.choice(self.operators)} Æ {_r.choice(self.operators)}",
            lambda: f"{_r.choice(self.operators)} → {_r.choice(self.operators)}",
            lambda: f"{_r.choice(self.operators)} Æ {_r.choice(self.operators)} Æ {_r.choice(self.operators)}",
            lambda: f"{_r.choice(self.operators)} = {_r.choice(['◎','✕'])}",
            lambda: f"{_r.choice(self.operators)} → {_r.choice(self.operators)} → {_r.choice(['$','Ω'])}",
            lambda: f"Σ{_r.choice(self.operators)} → {_r.choice(['M','ZK'])}",
            lambda: f"{_r.choice(self.operators)} stays @L ; {_r.choice(self.operators)} travels →",
            lambda: f"λ↓ → {_r.choice(self.operators)}↑ → $↑",
            lambda: f"{_r.choice(self.operators)} Æ T_window Æ {_r.choice(['◎','✕'])} → {_r.choice(['$','Ω'])}",
            lambda: f"Antonym:{_r.choice(['classify','blur','invert','redact'])} Æ {_r.choice(self.operators)}",
            lambda: f"Oracle:{_r.choice(['hidden_test','on_chain','expert'])} → {_r.choice(['◎','✕'])}",
            lambda: f"Bond:{_r.choice(['posted','returned','slashed'])} Æ {_r.choice(['◎','✕'])}",
            lambda: f"χ{_r.choice(['visual','file','process','power','snapshot'])} → LCI",
            lambda: f"Claim:{_r.choice(['artifact_existed','tests_passed','no_secrets'])} Æ ◎",
            lambda: f"{_r.choice(self.operators)} → R → λ⁻¹ → Δ{_r.choice(self.operators)} ⟲",
        ]
        return _r.choice(patterns)()

    def tick(self, count: int = None) -> list[dict]:
        """Generate one tick of glyphs (default: rate_per_min)."""
        n = count or self.rate_per_min
        emitted = []
        attempts = 0
        while len(emitted) < n and attempts < n * 10:
            symbol = self._generate_symbol()
            glyph = self._emit_glyph(symbol, "tick")
            if glyph:
                emitted.append(glyph)
            attempts += 1
        return emitted

    def stream(self, n: int = 20) -> list[dict]:
        """Get the last N glyphs as a live stream."""
        return self.glyphs[-n:]

    def stats(self) -> dict:
        return {
            "total_generated": self.total_generated,
            "unique_stored": len(self.glyphs),
            "duplicates_rejected": self.duplicates_rejected,
            "target": self.target_count,
            "rate_per_min": self.rate_per_min,
            "progress_pct": round(len(self.glyphs) / self.target_count * 100, 2),
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "ink_chain_head": self.ink_chain,
            "pen_continuity": "unbroken" if self.total_generated > 0 else "idle",
            "glyphs_remaining": max(0, self.target_count - len(self.glyphs)),
            "eta_minutes": round(max(0, self.target_count - len(self.glyphs)) / max(self.rate_per_min, 1), 1),
        }

    def to_json(self) -> str:
        return json.dumps({
            "stats": self.stats(),
            "recent": self.stream(50),
        }, indent=2)


# --- CLI ---
def cli():
    if len(sys.argv) < 2:
        print("GlyphLang — Glyphgramming Language Compiler")
        print()
        print("Usage:")
        print("  python3 glyphlang.py compile <file.glyph>   Compile a .glyph program")
        print("  python3 glyphlang.py run <file.glyph>       Compile + execute")
        print("  python3 glyphlang.py repl                   Interactive glyph REPL")
        print("  python3 glyphlang.py ink                    Start InkStream engine")
        print("  python3 glyphlang.py demo                   Run demo program")
        sys.exit(0)

    cmd = sys.argv[1]
    compiler = GlyphCompiler()

    if cmd == "compile":
        if len(sys.argv) < 3:
            print("Error: file path required")
            sys.exit(1)
        source = Path(sys.argv[2]).read_text()
        result = compiler.compile(source)
        print(f"Program: {result['program']['name']}")
        print(f"Hash: {result['hash']}")
        print(f"Tokens: {result['token_count']}")
        print(f"Statements: {result['statement_count']}")
        print(f"Status: {result['status']}")
        print(f"Targets: {result['targets']}")
        if result["errors"]:
            print(f"Errors: {result['errors']}")
        for target, code in result["outputs"].items():
            print()
            print(f"--- {target.upper()} ---")
            print(code)

    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Error: file path required")
            sys.exit(1)
        source = Path(sys.argv[2]).read_text()
        result = compiler.execute(source)
        print(f"Program: {result['program']['name']}")
        print(f"Status: {result['status']}")
        print(f"Receipts: {result.get('receipt_count', 0)}")
        if result.get("receipts"):
            for r in result["receipts"]:
                print(f"  {r}")

    elif cmd == "repl":
        print("GlyphLang REPL — type glyph sequences, Ctrl+C to exit")
        print("Example: ◇@L → H@L Æ R Æ λ⁻¹ = ◎ → $")
        print()
        while True:
            try:
                line = input("glyph> ")
                if not line.strip():
                    continue
                result = compiler.compile(f"program REPL\n  {line}\nend")
                print(f"  tokens={result['token_count']} stmts={result['statement_count']} status={result['status']}")
                if result["errors"]:
                    for e in result["errors"]:
                        print(f"  ERROR: {e}")
            except KeyboardInterrupt:
                print("\nbye")
                break

    elif cmd == "ink":
        print("InkStream — Continuous Pen-Continuity Glyph Engine")
        print(f"Target: 234,322 glyphs at 34/min")
        print("Press Ctrl+C to stop")
        print()
        stream = InkStream()
        try:
            while True:
                emitted = stream.tick()
                stats = stream.stats()
                print(f"[{stats['unique_stored']:6d}/{stats['target']}] {stats['progress_pct']:5.1f}% | +{len(emitted)} glyphs | chain={stats['ink_chain_head']} | pen={stats['pen_continuity']}")
                time.sleep(60 / stream.rate_per_min)
        except KeyboardInterrupt:
            print(f"\nFinal: {stream.stats()}")

    elif cmd == "demo":
        demo = """program DemoWorkflow
  ◇@L → H@L
  H@L Æ R
  R Æ λ⁻¹
  λ⁻¹ = ◎
  ◎ → $
  emit ◇ Æ R Æ λ⁻¹ → $
end"""
        print("--- Source ---")
        print(demo)
        print()
        # Compile to all targets
        result = compiler.compile(demo)
        print(f"Program: {result['program']['name']}")
        print(f"Status: {result['status']}")
        print(f"Tokens: {result['token_count']}")
        print(f"Statements: {result['statement_count']}")
        print(f"Targets: {result['targets']}")
        print()
        # Execute Python version
        exec_result = compiler.execute(demo)
        print(f"Execution: {exec_result['status']}, receipts={exec_result.get('receipt_count', 0)}")
        if exec_result.get("receipts"):
            for r in exec_result["receipts"]:
                print(f"  {r}")
        print()
        # Show all target outputs
        for target, code in result["outputs"].items():
            print(f"--- {target.upper()} ---")
            print(code)
            print()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
