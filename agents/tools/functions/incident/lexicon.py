"""Multilingual incident-signal detection (English, Bahasa Malaysia, Chinese, Manglish).

Deterministic regular-expression rules, no model and no new dependency. Each
rule maps a clause of the user's text to a *signal kind*. Detection is
guarded so that questions, negation, hypotheticals, instructions the scammer
gave, hedged statements and quoted text are not read as "the user did this".

Known limits (do not oversell): vocabulary is finite and hand-written, so
unusual slang, Traditional-Chinese wording, Tamil, Jawi and misspellings are
mostly missed; clause splitting can lose the object of a verb across a comma;
and a statement that shows no scam context at all is ignored unless an earlier
turn or a high-risk assessment supplies that context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_F = re.IGNORECASE


def _c(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, _F)


# --------------------------------------------------------------------------
# Language detection (used to choose the response language)
# --------------------------------------------------------------------------

_CJK = re.compile(r"[一-鿿]")
_MS_WORDS = frozenset(
    "saya dah sudah telah tak tidak belum duit wang bayar kena tipu penipu penipuan bagi beri "
    "kod kata laluan akaun dia mereka tolong macam nak yang dan untuk dengan ini itu tu tadi "
    "lagi rasa mungkin tapi tetapi kepada selepas lepas pegawai polis hantar tekan masuk "
    "pasang aplikasi telefon betul ke apa bila boleh sebab sekarang ada orang".split()
)
_EN_WORDS = frozenset(
    "the i my and to a is it he they that was have now what me you for of in on with this "
    "not but are been did do would should from after so just".split()
)


def detect_language(text: str) -> str:
    """Return "zh", "ms" or "en". Manglish with mostly English words stays "en"."""
    if len(_CJK.findall(text)) >= 2:
        return "zh"
    words = re.findall(r"[a-z']+", text.casefold())
    ms = sum(1 for w in words if w in _MS_WORDS)
    en = sum(1 for w in words if w in _EN_WORDS)
    return "ms" if ms >= 3 and ms > en else "en"


# --------------------------------------------------------------------------
# Context gate: wording typical of a scam contact
# --------------------------------------------------------------------------

_SCAM_CONTEXT = _c(
    r"(?:\b(?:scam\w*|scammer\w*|fraud\w*|cheat\w*|conned|phish\w*|fake|suspicious|"
    r"unauthori[sz]ed|hack\w*|impersonat\w*|pos(?:e|ed|ing)\s+as|pretend\w*|claim(?:ed|ing)|"
    r"caller|stranger|someone\s+(?:called|messaged|texted|contacted|rang)|"
    r"(?:called|messaged|texted|contacted|rang)\s+me|mule|safe\s+account|police|pdrm|"
    r"bank\s+negara|bnm|lhdn|customs|court|parcel|courier|poslaju|dhl|j&t|delivery|"
    r"investment|returns?|profit|crypto|broker|forex|trading\s+(?:app|platform|group)|"
    r"job\s+offer|part[- ]time\s+job|task|romance|lottery|prize|lucky\s+draw|refund|compensation|"
    r"verify\s+your|agent|officer|sms|whatsapp|telegram|wechat|text\s+message|gift\s?cards?|"
    r"control\s+my\s+(?:phone|computer|laptop|device)|"
    r"(?:account|number|link|details?)\s+(?:that\s+)?(?:they|he|she)\s+(?:gave|sent|provided|told)|"
    # Bahasa Malaysia
    r"penipu\w*|penipuan|tipu\w*|ditipu|kena\s+(?:tipu|scam)|pegawai|polis|panggilan|"
    r"mengaku|akaun\s+selamat|pelaburan|cabutan\s+bertuah|hadiah|pinjaman|pos\s*laju|"
    r"mahkamah|palsu|tanpa\s+kebenaran|kerja\s+sambilan|mangsa|rupanya\s+(?:scam|penipuan|tipu)|mesej|"
    r"kawal\s+telefon|orang\s+kawal)\b|"
    # Chinese (no word boundaries between CJK characters)
    r"骗|诈骗|冒充|陌生|警察|警方|法院|客服|兼职|中奖|退款|远程|对方|未经授权|没有授权|"
    r"洗钱|涉嫌|短信|微信|假银行|假网站|假冒|投资平台|平台|被扣|被盗)"
)

_THIRD_PARTY = _c(
    r"(?:\b(?:them|him|her|someone|somebody|stranger|caller|person|guy|man|woman|agent|"
    r"officer|staff|they|he|she|website|site|page|dia|mereka|orang|penelefon|pegawai|"
    r"unknown|tidak\s+dikenali|tak\s+dikenali)\b|他|她|对方|骗子|陌生人|客服|别人|有人|网站|网页)"
)
CREDENTIAL_KINDS = frozenset({"financial_credentials", "other_credentials", "identity_documents"})


def has_scam_context(text: str) -> bool:
    return bool(_SCAM_CONTEXT.search(text))


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------

_PAST_SHARE_EN = (
    r"(?:gave|given|shared|sent|entered|typed|provided|submitted|disclosed|revealed|told|"
    r"keyed(?:\s+in)?|key(?:ed)?\s+in|put\s+in|read\s+out|replied\s+with|texted|filled\s+in|"
    r"inserted|uploaded|emailed|forwarded|handed\s+over)"
)
# Manglish/Malay verbs are often unmarked for tense; the irrealis guard drops
# "asked me to / should / will" readings instead.
_SHARE_MS = (
    r"(?:\w*(?:dah|sudah|telah|udah)\s+)?(?:ter(?:kongsi|bagi|beri|hantar|masuk)|bagi|beri|berikan|"
    r"kasi|kongsi|kongsikan|hantar|masukkan|masuk|taip|taipkan|bacakan|beritahu|sebut)"
)
_FIN_CRED_EN = (
    r"(?:otp|tac|one[- ]?time\s+(?:pass(?:code|word)|code|pin)|verification\s+code|"
    r"security\s+code|pin|cvv|cvc|card\s+(?:number|details|info)|(?:credit|debit)\s+card|"
    r"bank(?:ing)?\s+(?:password|login|details|credentials|info)|"
    r"(?:the|a|that|my)\s+(?:\d[- ]digit\s+)?(?:sms\s+|text\s+)?code|"
    r"(?:online|internet|mobile)\s+banking|secure\s*word|banking\s+app)"
)
_FIN_CRED_MS = (
    r"(?:kod\s+(?:otp|tac|pengesahan)|nombor\s+(?:tac|otp|pin|kad)|otp|tac|pin|cvv|"
    r"butiran\s+(?:kad|bank|perbankan)|no(?:mbor)?\s+kad(?:\s+kredit|\s+debit)?|"
    r"kata\s*laluan\s+(?:bank|perbankan|akaun\s+bank))"
)
_ANY_CRED_EN = r"(?:password|passcode|login\s+(?:details|credentials|info)|credentials|username|passphrase|login(?!\s*(?:page|screen|form|site)))"
_ANY_CRED_MS = r"(?:kata\s*laluan|katalaluan|password|id\s+pengguna|butiran\s+log\s*masuk)"
_MONEY_VERB_EN = (
    r"(?:transferred|paid|wired|sent|deposited|remitted|banked\s+in|topped\s+up|"
    r"invested|loaded|made\s+(?:a\s+)?(?:payment|transfer|deposit)|duitnow(?:ed)?)"
)
_MONEY_OBJ_EN = (
    r"(?:money|funds?|cash|rm\s?\d[\d,.]*|myr\s?\d|\$\s?\d|\d[\d,]*\s?(?:ringgit|myr|rm|usd|sgd|dollars?)|"
    r"\d+(?:\.\d+)?\s?(?:k|m|thousand|million)\b|payment|deposit|fees?|gift\s?cards?|bitcoin|btc|crypto|usdt|savings|salary|amount|"
    r"it\s+(?:all|to\s+them))"
)
_MONEY_AMT = r"(?:rm\s?\d\d*|myr\s?\d|\$\s?\d|\d+\s?(?:ringgit|myr|rm|usd|sgd|dollars?|k\b|thousand|million))"
_MONEY_OBJ_MS = r"(?:duit|wang|rm\s?\d|ringgit|yuran|bayaran|deposit|fi|caj|pelaburan|usdt|bitcoin|crypto|gaji|simpanan)"
_REMOTE_TOOLS = (
    r"(?:anydesk|teamviewer|ultraviewer|rustdesk|quick\s*support|supremo|ammyy|"
    r"remote\s+(?:access|control|desktop|support)|kawalan\s+jauh|akses\s+jauh)"
)

# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    kind: str
    pattern: re.Pattern[str]
    ctx_free: bool = False  # inherently contextual: needs no other scam wording
    irrealis: bool = False  # also drop "asked/told/should/will" readings (ms, zh)
    third_ok: bool = False  # the rule names its own subject, so skip the "someone else did it" guard
    benign_after: bool = False  # drop when a legitimate purpose follows ("to help my parents")


def _r(
    kind: str,
    pattern: str,
    *,
    ctx_free: bool = False,
    irrealis: bool = False,
    third_ok: bool = False,
    benign_after: bool = False,
) -> Rule:
    return Rule(kind, _c(pattern), ctx_free, irrealis, third_ok, benign_after)


RULES: tuple[Rule, ...] = (
    # ---- English: money ----
    _r("money_sent", rf"\b{_MONEY_VERB_EN}\b[^.]{{0,60}}?\b{_MONEY_OBJ_EN}"),
    _r("money_sent", r"\bi\s+(?:have\s+|'ve\s+|already\s+|just\s+)*(?:paid|transferred)\b"),
    _r("money_sent", r"\b(?:already|just(?:\s+now)?)\s+(?:transfer|pay|wire|deposit)\b"),  # Manglish
    _r("money_sent", rf"\b(?:lost|scammed\s+(?:of|out\s+of))\s+{_MONEY_AMT}"),
    _r("money_sent", r"\b(?:money|funds?|savings|rm\s?\d[\d,.]*)\b[^.]{0,30}\b(?:was|were|got|has\s+been|have\s+been)?\s*"
                     r"(?:deducted|debited|withdrawn|drained|missing|gone|stolen|taken)\b", ctx_free=True, third_ok=True),
    _r("money_sent", r"\bunauthori[sz]ed\s+(?:transaction|transfer|withdrawal|payment|debit)s?\b", ctx_free=True, third_ok=True),
    _r("money_sent", r"\b(?:they|he|she|scammers?|someone)\s+(?:took|stole|withdrew|drained)\b[^.]{0,30}\b(?:money|funds?|account|savings)\b", third_ok=True),
    # ---- English: credentials ----
    _r("financial_credentials", rf"\b{_PAST_SHARE_EN}\b[^.]{{0,50}}?\b{_FIN_CRED_EN}\b"),
    _r("financial_credentials", rf"\b(?:they|he|she|scammers?|caller|someone|hackers?)\s+(?:got|has|have|had|obtained|knows?)\b[^.]{{0,15}}\b(?:my\s+)?{_FIN_CRED_EN}\b", third_ok=True),
    _r("other_credentials", rf"\b{_PAST_SHARE_EN}\b[^.]{{0,50}}?\b{_ANY_CRED_EN}\b"),
    _r("other_credentials", rf"\b(?:they|he|she|scammers?|caller|someone|hackers?)\s+(?:got|has|have|had|obtained|knows?)\b[^.]{{0,15}}\b(?:my\s+)?{_ANY_CRED_EN}\b", third_ok=True),
    _r("data_entered_on_site", r"\b(?:filled\s+(?:in|out)|entered|submitted|typed)\b[^.]{0,40}\b(?:form|website|site|page|portal)\b"),
    _r("link_interaction", r"\b(?:clicked|tapped|opened|pressed|visited|followed)\b[^.]{0,25}\b(?:link|url|website|button|attachment)\b"),
    # ---- English: device ----
    _r("remote_access", rf"\b(?:gave|given|granted|allowed|let|installed|downloaded|opened|started|connected)\b[^.]{{0,40}}?\b{_REMOTE_TOOLS}\b", benign_after=True),
    _r("remote_access", rf"\b(?:made|forced|tricked|convinced|got)\s+me\s+(?:to\s+)?(?:install|download|open|use|start)\b[^.]{{0,40}}?\b{_REMOTE_TOOLS}\b"),
    _r("remote_access", r"\b(?:gave|given|granted|allowed|let)\b[^.]{0,20}\b(?:them|him|her|the\s+caller|someone)\b[^.]{0,20}\b(?:control|access)\b"),
    _r("remote_access", r"\b(?:they|he|she|someone|the\s+scammer|scammers?)\s+(?:can|could)\s+(?:now\s+)?(?:control|see|access)\s+my\s+(?:phone|computer|laptop|device|screen)\b", ctx_free=True, third_ok=True),
    _r("app_installed", r"\b(?:installed|downloaded|sideloaded)\b[^.]{0,40}\b(?:apk|app|application|software|file)\b", benign_after=True),
    _r("app_installed", r"\b(?:sideloaded|installed|downloaded)\s+(?:it|them|the\s+(?:file|apk|app))\b", benign_after=True),
    _r("identity_documents", rf"\b{_PAST_SHARE_EN}\b[^.]{{0,50}}?\b(?:ic|mykad|nric|passport|identity\s+card|id\s+card|selfie|photo\s+of\s+my\s+(?:ic|id|face)|face\s+scan|ic\s+number)\b"),
    _r("unspecified_victim",
       r"\b(?:i(?:'m|\s+am|\s+was|\s+got|\s+have\s+been|'ve\s+been)\s+(?:a\s+victim\s+of\s+)?"
       r"(?:scammed|cheated|conned|defrauded|phished|hacked)|scam\s+victim|victim\s+of\s+(?:a\s+)?scam|"
       r"i\s+fell\s+for|i\s+(?:followed|did)\s+(?:what\s+)?(?:their|the|they|he|she)\b[^.]{0,20}(?:instructions?|said|told|asked)|"
       r"i\s+(?:replied|responded|complied|went\s+along)|"
       r"(?:i\s+was|i\s+am|i'm|i\s+had\s+been)\s+(?:dealing|talking|chatting|speaking)\s+(?:with|to)\s+(?:a\s+|an\s+)?(?:scammer|fraudster|con\s*artist)|"
       r"i\s+realis?ed\b[^.]{0,30}\b(?:scam|scammer|fraud|cheated|conned)|"
       r"it\s+(?:was|turned\s+out\s+to\s+be)\s+(?:a\s+)?(?:scam|fraud)|turned\s+out\s+(?:to\s+be\s+)?(?:a\s+)?(?:scam|fraud))\b", ctx_free=True),
    # ---- Bahasa Malaysia / Manglish ----
    _r("money_sent", r"\b(?:dah|sudah|telah|udah)\s+(?:transfer|bayar|labur|deposit)\w*", irrealis=True),
    _r("money_sent", r"\b(?:buat|membuat|lakukan|melakukan)\s+(?:satu\s+)?(?:pembayaran|pemindahan|transaksi|bayaran)\b", irrealis=True),
    _r("money_sent", rf"\b(?:transfer|bayar|labur|deposit)\w*\b[^.]{{0,30}}\b{_MONEY_AMT}", irrealis=True),
    _r("unspecified_victim", r"\brupanya\s+(?:scam|penipuan|tipu)\b", ctx_free=True),
    _r("money_sent", rf"\b(?:dah|sudah|telah|udah)\s+(?:hantar|bagi|beri|kasi)\w*\s+(?:\w+\s+){{0,2}}{_MONEY_OBJ_MS}", irrealis=True),
    _r("money_sent", r"\b(?:duit|wang|simpanan)\b[^.]{0,40}\b(?:hilang|lesap|dikeluarkan|ditarik|dicuri|kena\s+(?:keluar|tarik|curi))\b", ctx_free=True, third_ok=True),
    _r("money_sent", r"\btransaksi\s+(?:tanpa\s+kebenaran|tidak\s+dibenarkan|yang\s+tidak\s+saya)\b", ctx_free=True, third_ok=True),
    _r("financial_credentials", rf"\b{_SHARE_MS}\b[^.]{{0,40}}?\b{_FIN_CRED_MS}\b", irrealis=True),
    _r("other_credentials", rf"\b{_SHARE_MS}\b[^.]{{0,40}}?\b{_ANY_CRED_MS}\b", irrealis=True),
    _r("data_entered_on_site", r"\b(?:masuk|masukkan|isi|taip)\w*\b[^.]{0,25}\b(?:borang|laman\s+web|web|pautan|link)\b", irrealis=True),
    _r("link_interaction", r"\b(?:tekan|tertekan|klik|terklik|buka|bukak|ter(?:buka))\w*\s+[^.]{0,20}\b(?:link|pautan|url|laman\s+web|lampiran)\b", irrealis=True),
    _r("remote_access", rf"\b(?:dah|sudah|telah|udah)?\s*(?:pasang|install|muat\s*turun|download|benarkan|beri\s+akses)\w*\s+[^.]{{0,25}}\b{_REMOTE_TOOLS}\b", irrealis=True),
    _r("app_installed", r"\b(?:dah|sudah|telah|udah)\s+(?:pasang|install|muat\s*turun|download)\w*\s+[^.]{0,25}\b(?:aplikasi|apk|app|perisian|fail)\b", irrealis=True),
    _r("identity_documents", rf"\b{_SHARE_MS}\b[^.]{{0,40}}?\b(?:ic|mykad|kad\s+pengenalan|pasport|passport|selfie|gambar\s+muka)\b", irrealis=True),
    _r("unspecified_victim", r"\b(?:kena\s+(?:tipu|scam)|ditipu|jadi\s+mangsa\s+(?:penipuan|scam))\b", ctx_free=True, third_ok=True),
    # ---- Chinese (no \b) ----
    _r("money_sent", r"(?:转账|汇款|付款|充值|转钱|打钱|付钱)了|已经?(?:转账|汇款|付款|充值|转钱|打钱)|(?:转|汇|付|打)了[^，。]{0,6}(?:钱|款|令吉|元|块|\d)", irrealis=True),
    _r("money_sent", r"被(?:扣|转走|盗刷|划走|取走|盗)[^，。]{0,10}(?:\d|令吉|元|钱|款)", ctx_free=True, third_ok=True),
    _r("financial_credentials", r"把[^，。]{0,6}(?:验证码|校验码|动态码|短信验证码|tac|otp|银行卡号|卡号|银行卡密码|网银密码|支付密码|pin码?|cvv)[^，。]{0,8}(?:告诉|发给|给|读给|报给|交给)", irrealis=True),
    _r("financial_credentials", r"(?:告诉|发给|给|发|读|报|透露|泄露|输入|填了|填写|提交)了[^，。]{0,8}(?:验证码|校验码|动态码|tac|otp|银行卡号|卡号|银行卡密码|网银密码|支付密码|pin码?|cvv)", irrealis=True),
    _r("other_credentials", r"(?:告诉|发给|给|发|输入|填写|填|提交|泄露)了[^，。]{0,8}(?:账号和密码|账号密码|帐号密码|登录密码|登录信息|密码)", irrealis=True),
    _r("other_credentials", r"把[^，。]{0,6}(?:登录密码|账号密码|密码)[^，。]{0,8}(?:告诉|发给|给|交给)", irrealis=True),
    _r("link_interaction", r"点(?:了|开|击)[^，。]{0,8}(?:链接|连接|网址)|打开了[^，。]{0,8}(?:链接|网址)", irrealis=True),
    _r("app_installed", r"(?:下载|安装)了[^，。]{0,10}(?:apk|应用|软件|app|程序)", irrealis=True),
    _r("remote_access", r"(?:下载|安装|装|授权|允许|开启)了[^，。]{0,10}(?:远程|anydesk|teamviewer|向日葵|todesk|屏幕共享|共享屏幕)", irrealis=True),
    _r("identity_documents", r"把[^，。]{0,12}(?:身份证|护照|自拍|人脸)[^，。]{0,12}(?:发给|给|交给|发送给|拍给)|(?:发|给|拍|上传|提供|发送)了[^，。]{0,12}(?:身份证|护照|自拍|人脸)", irrealis=True),
    _r("unspecified_victim", r"(?:被骗|上当|受骗|被诈骗|中了(?:圈套|骗局))", ctx_free=True, third_ok=True),
)

# --------------------------------------------------------------------------
# Guards (applied to the text just before a match)
# --------------------------------------------------------------------------

_NEGATION = _c(
    r"(?:\b(?:not|never|didn'?t|did\s+not|haven'?t|have\s+not|hasn'?t|won'?t|wouldn'?t|without|no|"
    r"belum|tak|tidak|tiada|bukan|jangan)\b|没有|还没|尚未|并未|并没有|从未|不曾|未曾|不要|没|别|无)[^.。，]{0,25}$"
)
# "not sure if I paid" is uncertainty, not negation, so check it first.
_HEDGE_STRONG = _c(
    r"(?:\bnot\s+(?:sure|certain)|\bunsure|\bdon'?t\s+(?:know|remember)|\bcan'?t\s+remember|"
    r"\btak\s+pasti|\btidak\s+pasti|不太确定|不确定|不知道是不是|不记得)[^,.。，]{0,25}$"
)
_HEDGE = _c(
    r"(?:\b(?:may|might|maybe|possibly|probably|perhaps|i\s+think|i\s+guess|i\s+believe|if|before|"
    r"whether|unless|in\s+case|what\s+if|should|would|could|mungkin|rasanya|agaknya|kot|"
    r"macam\s+(?:nya|kena)|kalau|jika|sekiranya)\b|可能|也许|或许|好像|似乎|应该|大概|说不定|"
    r"我想|我觉得|如果|假如|万一)[^,.。，]{0,25}$"
)
# Only for Malay/Chinese rules: an instruction or plan, not something done.
_IRREALIS = _c(
    r"(?:\b(?:suruh|minta|disuruh|diminta|nak|hendak|akan|patut|perlu|boleh\s+ke|patutkah|"
    r"kena\s+(?:bagi|beri|hantar|transfer|bayar))\b|让我|叫我|要我|要求我|逼我|说要|想要|打算|准备|"
    r"是否要|该不该|要不要)[^,.。，]{0,25}$"
)
# Someone else's actions: "my friend … transferred", "the news said a woman lost …".
_THIRD_SUBJECT = _c(
    r"(?:\b(?:he|she|they|friend|friends|mum|mom|mother|dad|father|wife|husband|brother|sister|"
    r"colleague|boss|neighbou?r|victims?|people|woman|man|lady|guy|someone|somebody|news|report|"
    r"article|kawan|dia|mereka|ibu|bapa|isteri|suami)\b|他们?|她们?|朋友|妈妈|爸爸|老婆|老公|同事|别人|有人|受害者)"
)
_FIRST_PERSON = _c(r"(?:\b(?:i|i'm|i've|me|my|we|our|saya|aku|kita|kami)\b|我)")
# A legitimate purpose right after an install ("installed AnyDesk to help my parents").
_BENIGN_AFTER = _c(
    r"^\s*(?:\w+\s+){0,6}?(?:to\s+(?:help|assist|fix|support)|for\s+(?:work|my\s+(?:job|work|office)|"
    r"tech(?:nical)?\s+support)|untuk\s+(?:bantu|membantu|kerja))\b"
)
_QUOTED = _c(
    r"\"[^\"]{1,300}\"|“[^”]{1,300}”|「[^」]{1,300}」|『[^』]{1,300}』|«[^»]{1,300}»|"
    r"(?<![\w])'[^']{3,200}'(?![\w])"
)
_CLAUSE_SPLIT = _c(
    r"[.!?;\n。！？；，、：:]+|,|\bbut\b|\bhowever\b|\balthough\b|\band\s+then\b|\bthen\b|"
    r"\btapi\b|\btetapi\b|\bkemudian\b|\blepas\s+tu\b|但是|可是|不过|然后|而且"
)
_NUMBER_SEPARATORS = re.compile(r"(?<=\d)[,.](?=\d)")


def _own_action(before: str) -> bool:
    """False when the nearest preceding subject is someone else ("my friend … transferred")."""
    last_third = None
    for match in _THIRD_SUBJECT.finditer(before):
        last_third = match
    if last_third is None:
        return True
    return bool(_FIRST_PERSON.search(before[last_third.end() :]))


def _guard(clause: str, match: re.Match[str], rule: Rule) -> str | None:
    """Return "negated", "possible" or None for a rule match inside ``clause``."""
    start = match.start()
    before = clause[max(0, start - 40) : start]
    if _HEDGE_STRONG.search(before):
        return "possible"
    if _NEGATION.search(before):
        return "negated"
    if rule.irrealis and _IRREALIS.search(before):
        return "negated"
    if not rule.third_ok and not _own_action(clause[max(0, start - 60) : start]):
        return "negated"
    if rule.benign_after and _BENIGN_AFTER.search(clause[match.end() :]):
        return "negated"
    if _HEDGE.search(before):
        return "possible"
    return None


# --------------------------------------------------------------------------
# Whole-text rules (evidence spread across clauses)
# --------------------------------------------------------------------------

_LOSS_CONTEXT = _c(r"(?:\b(?:scam\w*|lost|fraud\w*|cheated|stolen|hacked|defrauded|victim|tipu|ditipu|kena\s+tipu)\b|被骗|诈骗|损失)")
_RECOVERY_VERB = _c(
    r"(?:\b(?:recover\w*|retriev\w*|get\s+(?:back|my\s+money\s+back)|reclaim\w*|unfreez\w*|"
    r"(?:release|withdraw)\s+(?:my|the|your)\s+(?:money|funds|investment)|"
    r"dapat(?:kan)?\s+balik|tuntut\s+balik|ambil\s+balik|pulangkan)\b|追回|要回|拿回|讨回|找回)"
)
_RECOVERY_FEE = _c(r"(?:\b(?:fees?|charges?|deposit|upfront|advance|commission|tax|yuran|bayaran|caj|komisen|bayar)\b|手续费|费用|保证金|先付|先交|佣金|解冻)")
_RECOVERY_OFFER = _c(
    r"(?:\b(?:recovery\s+(?:agent|service|company|specialist|lawyer|expert)|offer(?:ed|ing|s)?|contacted\s+me|"
    r"messaged\s+me|emailed|(?:he|she|they)\s+can|can\s+(?:get|help)|"
    r"ethical\s+hacker|tawar\w*|boleh\s+bantu|kata\s+boleh)\b|有人说|对方说|可以帮|能帮|帮你追|帮我追|代理|专家)"
)
_ZH_REMOTE_TOOL = _c(r"(?:远程控制|远程协助|远程软件|远程|anydesk|teamviewer|向日葵|todesk|屏幕共享)")
_ZH_DONE = _c(r"(?:已经?安装|已经?下载|安装了|下载了|装了|授权了|允许了|共享了)")
_QUESTION_START = _c(r"^\s*(?:what|how|why|please\s+explain|explain|can\s+you\s+explain|apa\s+itu|什么是|如何)")
_GIFT_CARD = _c(r"\bgift\s?cards?\b")
_GIFT_SHARED = _c(
    r"\b(?:read|sent|gave|told|shared|photograph\w*|took\s+a\s+(?:photo|picture))\b[^.]{0,30}"
    r"\b(?:numbers?|codes?|pins?|photos?|pictures?|back\s+of)\b"
)


def _whole_text_signals(text: str, found: dict[str, str], context_ok: bool) -> None:
    # Recovery scam: an offer to get lost money back, tied to a fee, after a loss.
    if (
        _RECOVERY_VERB.search(text)
        and _RECOVERY_FEE.search(text)
        and _RECOVERY_OFFER.search(text)
        and _LOSS_CONTEXT.search(text)
        and not _QUESTION_START.match(text)
    ):
        found.setdefault("recovery_scam", "confirmed")
    # Gift-card scams: the money moves when the card numbers are read out or photographed.
    if _GIFT_CARD.search(text) and _GIFT_SHARED.search(text) and (context_ok or found):
        found.setdefault("money_sent", "confirmed")
    # Chinese: install verb and tool name often sit in different clauses.
    if context_ok and _ZH_REMOTE_TOOL.search(text) and _ZH_DONE.search(text):
        match = _ZH_DONE.search(text)
        before = text[max(0, match.start() - 8) : match.start()]
        if not _NEGATION.search(before) and found.get("remote_access") != "confirmed":
            found["remote_access"] = "confirmed"


# Entering data after opening a link is the phishing pattern by itself.
_CORROBORATED_BY_LINK = frozenset(
    {"other_credentials", "financial_credentials", "data_entered_on_site"}
)


def detect_signals(text: str, context_ok: bool) -> dict[str, str]:
    """Map signal kind -> strongest status ("confirmed" beats "possible").

    Pass 1 collects every guarded match. Pass 2 keeps a match only if the text
    shows scam context, the rule is inherently contextual, a credential or ID
    was handed to a third party, or opening a link and then entering data
    corroborate each other. That keeps "I entered my OTP to log in" quiet.
    """
    raw: dict[str, dict[str, object]] = {}
    normalized = _NUMBER_SEPARATORS.sub("", text)
    masked = _QUOTED.sub(" ", normalized)  # quoted text is someone else's words
    for clause in _CLAUSE_SPLIT.split(masked):
        clause = clause.strip()
        if not clause:
            continue
        third_party = bool(_THIRD_PARTY.search(clause))
        for rule in RULES:
            for match in rule.pattern.finditer(clause):
                guard = _guard(clause, match, rule)
                if guard == "negated":
                    continue
                status = "possible" if guard else "confirmed"
                entry = raw.setdefault(
                    rule.kind, {"status": status, "ctx_free": False, "third": False}
                )
                if status == "confirmed":
                    entry["status"] = "confirmed"
                entry["ctx_free"] = entry["ctx_free"] or rule.ctx_free
                entry["third"] = entry["third"] or (
                    third_party and rule.kind in CREDENTIAL_KINDS
                )

    link_seen = "link_interaction" in raw
    found: dict[str, str] = {}
    for kind, entry in raw.items():
        corroborated = link_seen and kind in _CORROBORATED_BY_LINK
        if context_ok or entry["ctx_free"] or entry["third"] or corroborated:
            found[kind] = str(entry["status"])
    if link_seen and "link_interaction" not in found and found.keys() & _CORROBORATED_BY_LINK:
        found["link_interaction"] = str(raw["link_interaction"]["status"])

    _whole_text_signals(masked, found, context_ok)
    # Specific signals subsume the generic ones they overlap with.
    if "remote_access" in found and "app_installed" in found:
        found.pop("app_installed")
    if "data_entered_on_site" in found and "link_interaction" in found:
        found.pop("link_interaction")
    if "unspecified_victim" in found and set(found) - {"unspecified_victim"}:
        found.pop("unspecified_victim")
    return found
