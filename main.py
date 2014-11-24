greek = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega"]
label_name_bases = greek
def get_label_name(n):
	if n < len(label_name_bases):
		return label_name_bases[n]
	return "%s%d" % (label_name_bases[n % len(label_name_bases)], n // len(label_name_bases))
def parse_line(x):
	x = x.strip()
	head, tail = x.split(": ")
	addr, off = head.split(" ")
	assert addr[0:2] == "0x" and len(addr) == 10
	assert off[0:2] == "<+" and off[-1] == ">"
	addrn = int(addr[2:], 16)
	offn = int(off[2:-1])
	if " " in tail:
		instr, args, *notes = tail.split(" ")
	else:
		instr, args, notes = tail, "", []
	return addrn, offn, instr, list(filter(None, args.split(","))), notes
def parse(fin):
	return [parse_line(x) for x in fin]
def ishex(x):
	return all(c in "0123456789ABCDEFabcdef" for c in x)
def targets(x, alltargets):
	addr, off, instr, args, notes = x
	out = []
	for a in args:
		if a[0:2] == "0x" and ishex(a[2:]) and int(a[2:], 16) in alltargets:
			out.append(int(a[2:], 16))
		elif a[0:3] == "$0x" and int(a[3:], 16) in alltargets:
			out.append(int(a[3:], 16))
	return out
registers = ["ebp", "esp", "esi", "edi", "eax", "ebx", "ecx", "edx"]
def is_register(x):
	return x[0] == "%" and x[1:] in registers
def is_constant(x):
	return x[0:2] == "0x"
def get_constant(x):
	assert is_constant(x)
	return int(x[2:], 16)
def describe_argument(x, targets):
	if is_register(x):
		return ("REG", x[1:])
	elif x[0] == "$" and is_constant(x[1:]):
		return ("NUM", get_constant(x[1:]))
	elif x[-1] == ")":
		a, b = x[:-1].split("(")
		if is_register(b):
			out = ("REG", b[1:])
			if not a:
				return ("MEM", out)
			elif is_constant(a):
				return ("MEM", ("ADD", out, get_constant(a)))
	return ()
def describe_instruction(x, targets):
	addr, off, instr, args, notes = x
	argsd = [describe_argument(arg, targets) for arg in reversed(args)] # REVERSE b/c AT&T syntax
	if not all(argsd):
		return ()
	l = len(argsd)
	o = ()
	if instr == "push" and l == 1:
		o = ("PUSH", argsd[0])
	elif instr == "mov" and l == 2 and argsd[0][0] == "REG":
		o = ("REG!", argsd[0][1], argsd[1])
	elif instr == "mov" and l == 2:
		o = ("SET", argsd[0], argsd[1])
	elif instr == "movl" and l == 2:
		o = ("SET", argsd[0], ("U4", argsd[1]))
	elif instr in ("and", "or", "add", "sub") and l == 2:
		o = ("SET", argsd[0], (instr.upper(), argsd[0], argsd[1]))
	if len(o) == 3 and o[0] == "SET" and o[1][0] == "REG":
		o = ("REG!", o[1][1], o[2])
	if len(o) == 3 and o[0] == "SET" and o[1][0] == "MEM":
		o = ("MEM!", o[1][1], o[2])
	return o
def lispstr(x):
	if type(x) == tuple:
		return "(" + " ".join(map(lispstr, x)) + ")"
	elif type(x) == int:
		return hex(x)
	return str(x)
def annotate(x, mlen, targets, p=print):
	addr, off, instr, args, notes = x
	addrnote = ""
	if addr in targets:
		addrnote += get_label_name(targets.index(addr))
	if off == 0:
		addrnote += "entry"
	starter = ("0x%.8x %8s @%" + str(mlen) + "d:  ") % (addr, addrnote, off)
	desc = describe_instruction(x, targets)
	if desc:
		p(starter, lispstr(desc))
	elif len(notes) == 1 and instr == "call" and notes[0][0] == "<" and notes[0][-1] == ">" and len(args) == 1:
		p(starter, "%4s %12s" % (instr, notes[0][1:-1]))
	else:
		p(starter, "%4s %s" % (instr, ",".join("%12s" % a for a in args + notes)))
with open("sample.s", "r") as f:
	datain = parse(f)
	alltargets = [x[0] for x in datain]
	mlen = max(len(str(x[1])) for x in datain)
	targets = list(sorted(set(sum((targets(x, alltargets) for x in datain), []))))
	print("Targets:", *map(hex,targets))
	for node in datain:
		annotate(node, mlen, targets)
