"""Text normalizer for TTS - converts abbreviations to phonetic form."""

import re

# Polish phonetic pronunciations for common tech terms
POLISH_PRONUNCIATIONS = {
    # Cloud providers & services
    "AWS": "a wu es",
    "GCP": "dżi si pi",
    "Azure": "ażur",
    
    # Programming & frameworks
    "Node.js": "nołd dżej es",
    "node.js": "nołd dżej es",
    "NodeJS": "nołd dżej es",
    "React.js": "riakt dżej es",
    "react.js": "riakt dżej es",
    "Vue.js": "wju dżej es",
    "vue.js": "wju dżej es",
    "Next.js": "nekst dżej es",
    "next.js": "nekst dżej es",
    "Express.js": "ekspres dżej es",
    "Nuxt.js": "nakst dżej es",
    "Three.js": "tri dżej es",
    "D3.js": "di tri dżej es",
    "JS": "dżej es",
    "JavaScript": "dżawa skrypt",
    "TypeScript": "tajp skrypt",
    "Python": "pajton",
    "PyTorch": "paj torch",
    "NumPy": "nam paj",
    "SciPy": "saj paj",
    
    # APIs & protocols
    "API": "A P I",
    "APIs": "A P I",
    "REST": "rest",
    "RESTful": "restful",
    "GraphQL": "graf kju el",
    "gRPC": "dżi ar pi si",
    "HTTP": "ha te te pe",
    "HTTPS": "ha te te pe es",
    "WebSocket": "łeb soket",
    "OAuth": "o ałf",
    "JWT": "dżej dablju ti",
    "JSON": "dżejson",
    "YAML": "jamel",
    "XML": "iks em el",
    "HTML": "ha te em el",
    "CSS": "si es es",
    "SQL": "es kju el",
    "NoSQL": "no es kju el",
    
    # AI & ML
    "AI": "A I",
    "ML": "em el",
    "LLM": "el el em",
    "LLMs": "el el emy",
    "GPT": "dżi pi ti",
    "GPT-4": "dżi pi ti cztery",
    "GPT-5": "dżi pi ti pięć",
    "ChatGPT": "czat dżi pi ti",
    "OpenAI": "open A I",
    "NLP": "en el pi",
    "GPU": "dżi pi ju",
    "GPUs": "dżi pi ju",
    "CPU": "si pi ju",
    "TPU": "ti pi ju",
    "CUDA": "kuda",
    "CNN": "si en en",
    "RNN": "ar en en",
    "LSTM": "el es ti em",
    "RAG": "rag",
    "TTS": "ti ti es",
    "STT": "es ti ti",
    
    # DevOps & Infrastructure
    "DevOps": "dewops",
    "CI/CD": "si aj si di",
    "CI": "si aj",
    "CD": "si di",
    "K8s": "kubernetes",
    "k8s": "kubernetes",
    "Docker": "doker",
    "VM": "wi em",
    "VMs": "wi emy",
    "VPC": "wi pi si",
    "EC2": "i si tu",
    "S3": "es trzy",
    "RDS": "ar di es",
    "ECS": "i si es",
    "EKS": "i kej es",
    "IAM": "aj ej em",
    "CDN": "si di en",
    "DNS": "di en es",
    "IP": "aj pi",
    "SSH": "es es hasz",
    "SSL": "es es el",
    "TLS": "ti el es",
    "VPN": "wi pi en",
    
    # Databases
    "PostgreSQL": "postgres kju el",
    "MySQL": "maj es kju el",
    "MongoDB": "mongo di bi",
    "Redis": "redis",
    "DynamoDB": "dynamo di bi",
    "SQLite": "es kju lajt",
    
    # Version control
    "Git": "git",
    "GitHub": "git hab",
    "GitLab": "git lab",
    "PR": "pi ar",
    "PRs": "pi ary",
    
    # Companies & products
    "Microsoft": "majkrosoft",
    "Google": "gugl",
    "Amazon": "amazon",
    "Netflix": "netfliks",
    "Spotify": "spotifaj",
    "Slack": "slak",
    "Zoom": "zum",
    "VS Code": "wi es kod",
    "VSCode": "wi es kod",
    "macOS": "mak o es",
    "iOS": "aj o es",
    "Linux": "linuks",
    "Ubuntu": "ubuntu",
    "Windows": "łindołs",
    "Chrome": "krom",
    "Firefox": "fajerfoks",
    
    # Other tech terms
    "SaaS": "sas",
    "PaaS": "pas",
    "IaaS": "jas",
    "IoT": "aj o ti",
    "AR": "ej ar",
    "VR": "wi ar",
    "XR": "iks ar",
    "SDK": "es di kej",
    "IDE": "aj di i",
    "CLI": "si el aj",
    "GUI": "dżi ju aj",
    "UI": "ju aj",
    "UX": "ju iks",
    "URL": "ju ar el",
    "URI": "ju ar aj",
    "UUID": "ju ju aj di",
    "regex": "redżeks",
    "RegEx": "redżeks",
    "async": "ejsink",
    "npm": "en pi em",
    "pip": "pip",
    "yarn": "jarn",
    "webpack": "łeb pak",
    "localhost": "lokal host",
    "README": "rid mi",
    "readme": "rid mi",
    "TODO": "tu du",
    "FIXME": "fiks mi",
    "FAQ": "ef ej kju",
    "etc.": "i tak dalej",
    "e.g.": "na przykład",
    "i.e.": "to znaczy",
    
    # DevOps & Development terms (from LLM suggestions)
    "repository": "re po zy to ri",
    "repo": "re po",
    "deployment": "di ploj ment",
    "deploy": "di ploj",
    "middleware": "mid l łer",
    "authentication": "o ten ty fi kej szyn",
    "auth": "ołf",
    "refactoring": "ri fak to ring",
    "refactor": "ri fak tor",
    "staging": "stej dżing",
    "backend": "bek end",
    "frontend": "front end",
    "legacy": "le ga si",
    "workflow": "łork floł",
    "serverless": "ser wer les",
    "microservices": "maj kro ser wi sys",
    "microservice": "maj kro ser wis",
    "containerized": "kon tej ne rajzd",
    "container": "kon tej ner",
    "orchestration": "or ke strej szyn",
    "pipeline": "pajp lajn",
    "CI/CD": "si aj si di",
    "DevOps": "dew ops",
    "GitOps": "git ops",
    "branch": "brancz",
    "merge": "merdż",
    "commit": "ko mit",
    "push": "pusz",
    "pull": "pul",
    "clone": "klon",
    "fork": "fork",
    "issue": "i szu",
    "sprint": "sprint",
    "scrum": "skram",
    "agile": "a dżajl",
    "kanban": "kan ban",
    "feature": "fi czer",
    "bug": "bag",
    "hotfix": "hot fiks",
    "release": "ri lis",
    "rollback": "rol bek",
    "downtime": "dałn tajm",
    "uptime": "ap tajm",
    "latency": "lej ten si",
    "throughput": "tru put",
    "scalability": "skej la bi li ti",
    "resilience": "re zy ljens",
    "monitoring": "mo ni to ring",
    "logging": "lo ging",
    "tracing": "trej sing",
    "debugging": "di ba ging",
    "profiling": "pro faj ling",
    "benchmarking": "bencz mar king",
    "caching": "ke szing",
    "cache": "kesz",
    "database": "dej ta bejs",
    "query": "kłi ri",
    "schema": "ski ma",
    "migration": "maj grej szyn",
    "backup": "bek ap",
    "restore": "ri stor",
    "snapshot": "snep szot",
    "cluster": "kla ster",
    "node": "nołd",
    "pod": "pod",
    "namespace": "nejm spejs",
    "ingress": "in gres",
    "egress": "i gres",
    "load balancer": "lołd ba lan ser",
    "proxy": "prok si",
    "gateway": "gejt łej",
    "endpoint": "end pojnt",
    "webhook": "łeb huk",
    "payload": "pej lołd",
    "header": "he der",
    "token": "to ken",
    "session": "se szyn",
    "cookie": "ku ki",
    "SSL": "es es el",
    "TLS": "ti el es",
    "certificate": "ser ty fi kat",
    "encryption": "en kryp szyn",
    "decryption": "di kryp szyn",
    "hashing": "he szing",
    "hash": "hesz",
    "salt": "solt",
    "password": "pas łord",
    "credentials": "kre den szals",
    "permission": "per mi szyn",
    "role": "rol",
    "policy": "po li si",
    "compliance": "kom plaj ens",
    "audit": "o dit",
    "vulnerability": "wul ne ra bi li ti",
    "exploit": "eks plojt",
    "patch": "pecz",
    "update": "ap dejt",
    "upgrade": "ap grejd",
    "downgrade": "dałn grejd",
    "version": "wer żyn",
    "changelog": "czejndż log",
    "readme": "rid mi",
    "documentation": "do kju men tej szyn",
    "tutorial": "tju to rial",
    "onboarding": "on bor ding",
    "boilerplate": "boj ler plejt",
    "scaffold": "ska fold",
    "template": "tem plejt",
    "snippet": "sni pet",
    "library": "laj bre ri",
    "package": "pa kidż",
    "module": "mo djul",
    "import": "im port",
    "export": "eks port",
    "dependency": "di pen den si",
    "dependencies": "di pen den sis",
    "runtime": "ran tajm",
    "compile": "kom pajl",
    "build": "bild",
    "bundle": "ban dl",
    "minify": "mi ni faj",
    "transpile": "trans pajl",
    "lint": "lint",
    "linter": "lin ter",
    "formatter": "for ma ter",
    "prettier": "pri ti er",
    "eslint": "i es lint",
    "webpack": "łeb pek",
    "vite": "wit",
    "rollup": "rol ap",
    "esbuild": "i es bild",
    "turbopack": "tur bo pek",
    
    # AWS & Cloud services
    "CloudWatch": "klałd łocz",
    "cloudwatch": "klałd łocz",
    "CloudFront": "klałd front",
    "CloudFormation": "klałd for mej szyn",
    "Lambda": "lam da",
    "lambda": "lam da",
    "DynamoDB": "daj na mo di bi",
    "S3": "es tri",
    "EC2": "i si tu",
    "ECS": "i si es",
    "EKS": "i kej es",
    "RDS": "ar di es",
    "SQS": "es kju es",
    "SNS": "es en es",
    "IAM": "aj em",
    "VPC": "wi pi si",
    "ELB": "i el bi",
    "ALB": "ej el bi",
    "NLB": "en el bi",
    "Route53": "rut fifty tri",
    "Cognito": "kog ni to",
    "Amplify": "em pli faj",
    "AppSync": "ep sink",
    "Athena": "a te na",
    "Redshift": "red szift",
    "Glue": "glu",
    "Kinesis": "ki ni sis",
    "SageMaker": "sejdż mej ker",
    "Bedrock": "bed rok",
    "CodePipeline": "kołd pajp lajn",
    "CodeBuild": "kołd bild",
    "CodeDeploy": "kołd di ploj",
    
    # Common programming terms from LLM
    "environment": "en waj ron ment",
    "function": "fan kszyn",
    "request": "ri kłest",
    "response": "ri spons",
    "review": "ri wju",
    "callback": "kol bek",
    "promise": "pro mis",
    "async": "ej sink",
    "await": "a łejt",
    "fetch": "fecz",
    "render": "ren der",
    "component": "kom po nent",
    "props": "props",
    "state": "stejt",
    "hook": "huk",
    "effect": "i fekt",
    "context": "kon tekst",
    "provider": "pro waj der",
    "consumer": "kon sju mer",
    "reducer": "ri dju ser",
    "action": "ek szyn",
    "dispatch": "dis pecz",
    "selector": "se lek tor",
    "middleware": "mid l łer",
    "store": "stor",
    "slice": "slajs",
    "thunk": "tank",
    "saga": "sa ga",
}

# English phonetic pronunciations
ENGLISH_PRONUNCIATIONS = {
    "AWS": "A W S",
    "API": "A P I",
    "APIs": "A P Is",
    "Node.js": "node J S",
    "node.js": "node J S",
    "AI": "A I",
    "ML": "M L",
    "LLM": "L L M",
    "GPU": "G P U",
    "CPU": "C P U",
    # Add more as needed
}


def normalize_text_for_tts(text: str, language: str = "pl") -> str:
    """
    Normalize text for TTS by replacing abbreviations with phonetic forms.
    
    Args:
        text: Input text with abbreviations.
        language: Target language ("pl" for Polish, "en" for English).
    
    Returns:
        Text with abbreviations replaced by phonetic pronunciations.
    """
    pronunciations = POLISH_PRONUNCIATIONS if language == "pl" else ENGLISH_PRONUNCIATIONS
    
    result = text
    
    # Sort by length (longest first) to avoid partial replacements
    sorted_terms = sorted(pronunciations.keys(), key=len, reverse=True)
    
    for term in sorted_terms:
        pronunciation = pronunciations[term]
        # Use word boundary matching to avoid replacing parts of words
        # But handle special cases like Node.js where . is part of the term
        if '.' in term:
            # Escape the dot for regex and match exactly
            pattern = re.escape(term)
            result = re.sub(pattern, pronunciation, result, flags=re.IGNORECASE)
        else:
            # Use word boundaries for regular terms
            pattern = r'\b' + re.escape(term) + r'\b'
            result = re.sub(pattern, pronunciation, result)
    
    # Clean up multiple spaces
    result = re.sub(r'\s+', ' ', result)
    
    return result


def add_custom_pronunciation(term: str, pronunciation: str, language: str = "pl"):
    """Add a custom pronunciation mapping."""
    if language == "pl":
        POLISH_PRONUNCIATIONS[term] = pronunciation
    else:
        ENGLISH_PRONUNCIATIONS[term] = pronunciation


def clean_script_for_tts(text: str) -> str:
    """
    Clean script text before TTS synthesis.
    
    Removes:
    - Markdown headers (##, ###)
    - Speaker labels ([HOST], [CO-HOST], HOST:, Co-Host:)
    - Continuation markers
    - Asterisks and bold markers
    - Empty parentheses and brackets
    - Stage directions in parentheses
    
    Args:
        text: Raw segment text that may contain metadata.
    
    Returns:
        Clean text ready for TTS synthesis.
    """
    result = text
    
    # Remove Markdown headers (## Kontynuacja, ### Temat 1, etc.)
    result = re.sub(r'^#{1,6}\s+.*?$', '', result, flags=re.MULTILINE)
    
    # Remove speaker labels - various formats
    # [HOST], [CO-HOST], [Prowadzący], etc.
    result = re.sub(r'\[(?:HOST|CO-HOST|PROWADZĄCY|WSPÓŁPROWADZĄCY|H|C)\][\s:]*', '', result, flags=re.IGNORECASE)
    # HOST:, Co-Host:, Prowadzący:, etc.
    result = re.sub(r'^(?:HOST|CO-HOST|PROWADZĄCY|WSPÓŁPROWADZĄCY|Host|Co-Host)[:\s]+', '', result, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove **bold** markers
    result = re.sub(r'\*\*([^*]+)\*\*', r'\1', result)
    result = re.sub(r'\*+', '', result)
    
    # Remove continuation markers in Polish and English
    result = re.sub(r'(?:kontynuacja|continuation|część\s*\d+|part\s*\d+)[\s:]*', '', result, flags=re.IGNORECASE)
    
    # Remove stage directions in parentheses (śmiech), (pauza), etc.
    result = re.sub(r'\([^)]{1,30}\)', '', result)
    
    # Remove empty brackets and parentheses
    result = re.sub(r'\[\s*\]|\(\s*\)', '', result)
    
    # Remove lines that are just metadata (INTRO:, OUTRO:, TEMAT 1:, etc.)
    result = re.sub(r'^(?:INTRO|OUTRO|TEMAT\s*\d*|TOPIC\s*\d*|SEGMENT\s*\d*)[:\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove URL-like patterns
    result = re.sub(r'https?://\S+', '', result)
    
    # Remove leftover markdown formatting
    result = re.sub(r'_{2,}|~{2,}|`+', '', result)
    
    # Normalize whitespace
    result = re.sub(r'\n{3,}', '\n\n', result)  # Max 2 newlines
    result = re.sub(r'[ \t]+', ' ', result)  # Multiple spaces to one
    result = re.sub(r'^\s+|\s+$', '', result, flags=re.MULTILINE)  # Trim lines
    
    return result.strip()


def detect_repetition_artifacts(text: str, min_repeat_length: int = 4, max_repeats: int = 3) -> bool:
    """
    Detect if text contains repetitive patterns that might indicate TTS/LLM loop artifacts.
    
    Common artifact patterns:
    - Same word repeated many times: "tak tak tak tak tak"
    - Syllable loops: "di on di on di on"
    - Character repetition: "aaaaaa"
    
    Args:
        text: Text to check for artifacts.
        min_repeat_length: Minimum length of pattern to detect (default 4 chars).
        max_repeats: Maximum allowed repetitions before flagging (default 3).
    
    Returns:
        True if suspicious repetition detected, False otherwise.
    """
    text_lower = text.lower()
    
    # Check for character repetition (aaaaa, eeeee)
    if re.search(r'(.)\1{5,}', text_lower):
        return True
    
    # Check for word repetition (tak tak tak tak)
    words = text_lower.split()
    if len(words) >= max_repeats + 1:
        for i in range(len(words) - max_repeats):
            if len(set(words[i:i+max_repeats+1])) == 1 and len(words[i]) >= 2:
                return True
    
    # Check for syllable/short pattern repetition (di on di on, cza di cza di)
    # Look for repeating 2-6 character patterns
    for pattern_len in range(2, 7):
        pattern = rf'(\S{{{pattern_len}}}(?:\s+\S{{{pattern_len}}})?)\s+\1\s+\1'
        if re.search(pattern, text_lower):
            return True
    
    # Check for unusually high ratio of repeated bigrams
    if len(words) >= 10:
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        bigram_counts = {}
        for bg in bigrams:
            bigram_counts[bg] = bigram_counts.get(bg, 0) + 1
        max_count = max(bigram_counts.values()) if bigram_counts else 0
        if max_count > max_repeats and max_count > len(bigrams) * 0.3:  # >30% same bigram
            return True
    
    return False


# =============================================================================
# XTTS GLITCH FIXES - Naprawia znane błędy syntezy polskiej
# =============================================================================

# Words that XTTS tends to spell out (literuje) instead of reading
XTTS_SPELLING_FIXES = {
    # "chce" często literowane jako "CE HA CE"
    "chce": "hce",
    "chcę": "hcę", 
    "chcesz": "hcesz",
    "chcemy": "hcemy",
    "chcą": "hcą",
    "chciał": "hciał",
    "chciała": "hciała",
    "chciałem": "hciałem",
    "chciałbym": "hciałbym",
    # Inne problematyczne
    "szcz": "szc",  # uproszczenie zbitki
}

# Abbreviations that MUST be expanded (XTTS stutters on them)
ABBREVIATION_EXPANSIONS = {
    "m.in.": "między innymi",
    "np.": "na przykład",
    "tzw.": "tak zwany",
    "tzn.": "to znaczy",
    "itp.": "i tym podobne",
    "itd.": "i tak dalej",
    "wg": "według",
    "ok.": "około",
    "dr": "doktor",
    "dr.": "doktor",
    "mgr": "magister",
    "mgr.": "magister",
    "inż.": "inżynier",
    "prof.": "profesor",
    "godz.": "godzina",
    "min.": "minut",
    "sek.": "sekund",
    "tys.": "tysięcy",
    "mln": "milionów",
    "mld": "miliardów",
    "zł": "złotych",
    "pkt": "punktów",
    "pkt.": "punktów",
    "r.": "roku",
    "w.": "wieku",
    "ub.": "ubiegłego",
    "br.": "bieżącego roku",
    "j.w.": "jak wyżej",
    "c.d.": "ciąg dalszy",
    "c.d.n.": "ciąg dalszy nastąpi",
    "b.r.": "bieżącego roku",
    "dn.": "dnia",
    "ds.": "do spraw",
    "tj.": "to jest",
    "pn.": "pod nazwą",
    "dot.": "dotyczący",
    "zob.": "zobacz",
    "por.": "porównaj",
    "pt.": "pod tytułem",
    "jw.": "jak wyżej",
    "dyr.": "dyrektor",
    "zast.": "zastępca",
    "prez.": "prezes",
    "przew.": "przewodniczący",
}

# Consonant clusters at word end that cause stuttering (add soft ending)
STUTTERING_CONSONANTS = ['rm', 'rn', 'lm', 'ln', 'sm', 'sn', 'tm', 'tn', 'km', 'kn', 'pm', 'pn']


def fix_xtts_glitches(text: str) -> str:
    """
    Fix known XTTS glitches for Polish language.
    
    Addresses:
    1. Words that get spelled out (literowanie)
    2. Abbreviations that cause stuttering
    3. Consonant clusters that cause pauses
    4. Single-letter words that confuse tokenizer
    
    Args:
        text: Input text
        
    Returns:
        Text with XTTS-friendly modifications
    """
    result = text
    
    # 1. Expand abbreviations (case-insensitive, word boundary)
    for abbrev, expansion in ABBREVIATION_EXPANSIONS.items():
        # Handle both with and without trailing space/punctuation
        # Use word boundary or start, and lookahead for end
        pattern = re.compile(r'(?<![a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ])' + re.escape(abbrev) + r'(?=\s|$|[,;:!?])', re.IGNORECASE)
        result = pattern.sub(expansion, result)
    
    # 2. Fix spelling-prone words (case-preserving replacement)
    for word, fix in XTTS_SPELLING_FIXES.items():
        # Case-insensitive match, preserve case in replacement
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        def replace_preserve_case(match):
            matched = match.group(0)
            if matched.isupper():
                return fix.upper()
            elif matched[0].isupper():
                return fix.capitalize()
            return fix
        result = pattern.sub(replace_preserve_case, result)
    
    # 3. Normalize multiple spaces
    result = re.sub(r'\s{2,}', ' ', result)
    
    # 4. Ensure proper sentence endings (helps XTTS with pacing)
    # Add comma after short clauses that might run together
    result = re.sub(r'(\w{2,})\s+(ale|więc|jednak|natomiast|czyli|dlatego)\s+', r'\1, \2 ', result)
    
    return result.strip()


def sanitize_segment_text(text: str, max_length: int = 500) -> str | None:
    """
    Full sanitization pipeline for segment text before TTS.
    
    Combines cleaning, normalization, and validation.
    Returns None if text is invalid/artifact.
    
    Args:
        text: Raw segment text.
        max_length: Maximum allowed segment length (to prevent TTS issues).
    
    Returns:
        Sanitized text or None if text should be skipped.
    """
    # Clean metadata first
    cleaned = clean_script_for_tts(text)
    
    # Check for artifacts
    if detect_repetition_artifacts(cleaned):
        return None
    
    # Check minimum meaningful content
    if not cleaned or len(cleaned.strip()) < 10:
        return None
    
    # Apply XTTS glitch fixes (abbreviations, spelling-prone words)
    cleaned = fix_xtts_glitches(cleaned)
    
    # Truncate overly long segments (can cause TTS quality issues)
    if len(cleaned) > max_length:
        # Try to truncate at sentence boundary
        truncated = cleaned[:max_length]
        last_sentence = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        if last_sentence > max_length * 0.7:  # Found sentence end in last 30%
            cleaned = truncated[:last_sentence + 1]
        else:
            cleaned = truncated.rsplit(' ', 1)[0] + '...'
    
    return cleaned
