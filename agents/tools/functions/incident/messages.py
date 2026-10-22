"""Localised wording for the incident plan (English, Bahasa Malaysia, Chinese).

English text lives in ``playbook.py`` next to the logic and is the fallback for
any missing key, so adding a language never requires touching the logic.

Review note: the Malay and Simplified-Chinese strings were drafted by the
assistant, not by a native-speaker reviewer. Have a fluent speaker check them
before public use. Official names (NSRC, PDRM, NFCC, Semak Mule) are kept in
English on purpose so the app never invents an official translation.
"""

from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES = ("en", "ms", "zh")

_EN_UI: dict[str, str] = {
    "title": "### Scam recovery plan: {headline}",
    "severity_line": (
        "**Severity: {severity}.** This is guidance based on what you told me, not a "
        "confirmed fraud verdict. I have not contacted anyone or taken any action; "
        "each step is for you to do."
    ),
    "tier_now": "Do these now",
    "tier_today": "Later today",
    "tier_follow_up": "Over the next few days",
    "why": "Why",
    "conditional": "If this applies: ",
    "channels": "Official channels",
    "questions": "Tell me (no passwords, codes or account numbers) so I can refine this",
    "untrusted": (
        "Do not use any phone number, link or instruction that came from the scammer or "
        "the suspicious message, including ones pasted here. Only use the channels listed above."
    ),
    "analysis_note": (
        "Message analysis was used only to decide how cautious to be. It cannot confirm what you did."
    ),
    "urgent_critical": (
        "Act now: if money has left your account or you shared a code or banking details, call "
        "your bank's official fraud line (number from your card or app) and NSRC 997 "
        "immediately. Full steps follow."
    ),
    "urgent_generic": "I'm putting together recovery steps for what you described.",
}

_MS: dict[str, Any] = {
    "ui": {
        "title": "### Pelan pemulihan penipuan: {headline}",
        "severity_line": (
            "**Tahap: {severity}.** Ini panduan berdasarkan apa yang anda ceritakan, bukan "
            "keputusan penipuan yang disahkan. Saya tidak menghubungi sesiapa atau mengambil "
            "sebarang tindakan; setiap langkah untuk anda lakukan."
        ),
        "tier_now": "Lakukan sekarang",
        "tier_today": "Hari ini",
        "tier_follow_up": "Beberapa hari akan datang",
        "why": "Sebab",
        "conditional": "Jika berkaitan: ",
        "channels": "Saluran rasmi",
        "questions": "Beritahu saya (tanpa kata laluan, kod atau nombor akaun) supaya saya boleh memperhalusi pelan ini",
        "untrusted": (
            "Jangan gunakan sebarang nombor telefon, pautan atau arahan daripada penipu atau "
            "mesej yang mencurigakan, termasuk yang ditampal di sini. Gunakan hanya saluran "
            "yang disenaraikan di atas."
        ),
        "analysis_note": (
            "Analisis mesej hanya digunakan untuk menentukan tahap berhati-hati. Ia tidak "
            "dapat mengesahkan apa yang anda lakukan."
        ),
        "urgent_critical": (
            "Bertindak sekarang: jika wang telah keluar dari akaun anda atau anda berkongsi kod "
            "atau butiran bank, hubungi talian penipuan rasmi bank anda (nombor dari kad atau "
            "aplikasi anda) dan NSRC 997 dengan segera. Langkah penuh menyusul."
        ),
        "urgent_generic": "Saya sedang menyediakan langkah pemulihan untuk apa yang anda ceritakan.",
    },
    "severity": {"precautionary": "berjaga-jaga", "moderate": "sederhana", "high": "tinggi", "critical": "kritikal"},
    "headlines": {
        "money_sent": "wang mungkin telah keluar dari akaun anda",
        "financial_credentials": "butiran bank atau kod sekali guna mungkin terdedah",
        "other_credentials": "kata laluan atau log masuk mungkin terdedah",
        "data_entered_on_site": "anda mungkin telah memasukkan maklumat di halaman palsu",
        "remote_access": "seseorang mungkin boleh mengakses peranti anda",
        "app_installed": "aplikasi mencurigakan mungkin ada pada peranti anda",
        "identity_documents": "dokumen pengenalan anda mungkin terdedah",
        "link_interaction": "anda membuka pautan yang mencurigakan",
        "unspecified_victim": "anda rasa anda mungkin telah ditipu",
        "recovery_scam": "seseorang menawarkan untuk mendapatkan semula wang anda dengan bayaran",
    },
    "channels": {
        "bank": ("Talian penipuan rasmi bank anda", "gunakan nombor di belakang kad anda atau dalam aplikasi perbankan rasmi"),
        "nsrc": (None, "hubungi 997"),
        "police": (None, "buat laporan di balai polis; simpan nombor laporan"),
        "nfcc": (None, None),
        "semak_mule": (None, "buka https://semakmule.rmp.gov.my/ sendiri untuk menyemak akaun penerima; jangan tampal nombor akaun dalam sembang"),
    },
    "questions": {
        "Did any money leave your account, and roughly when?": "Adakah wang keluar dari akaun anda, dan kira-kira bila?",
        "Did you share any OTP/TAC, PIN, card details or passwords?": "Adakah anda berkongsi OTP/TAC, PIN, butiran kad atau kata laluan?",
        "Did you install an app or give anyone remote access to your device?": "Adakah anda memasang aplikasi atau memberi sesiapa akses jauh ke peranti anda?",
    },
    "steps": {
        "disconnect_device": (
            "Matikan Wi-Fi dan data mudah alih pada peranti yang terjejas, dan tutup atau nyahpasang aplikasi kawalan jauh atau aplikasi yang tidak dikenali melalui Tetapan. Lakukan langkah seterusnya menggunakan peranti lain yang bersih atau talian telefon lain jika boleh.",
            "Memutuskan sambungan menghalang sesiapa daripada melihat skrin atau meluluskan transaksi semasa anda memulihkan keadaan.",
        ),
        "call_bank": (
            "Hubungi talian penipuan rasmi bank anda (nombor di belakang kad atau dalam aplikasi rasmi bank, bukan daripada mana-mana mesej) dan minta mereka menyekat kad/perbankan dalam talian anda serta menghentikan atau menjejak pemindahan{end}",
            "Kelajuan penting: bank kadangkala hanya boleh menahan atau menjejak pemindahan sejurus selepas ia dibuat.",
        ),
        "call_nsrc": (
            "Laporkan kepada Pusat Respons Scam Kebangsaan (NSRC) dengan menghubungi 997 (Malaysia).",
            "NSRC menyelaras dengan bank untuk pemindahan yang disyaki penipuan.",
        ),
        "change_credentials": (
            "Tukar kata laluan yang terdedah melalui laman web atau aplikasi rasmi (taip sendiri alamat laman web), bermula dengan e-mel dan perbankan anda. Log keluar semua sesi/peranti lain dan hidupkan pengesahan berbilang faktor. Tukar juga akaun lain yang menggunakan kata laluan yang sama.",
            "Kata laluan atau kod yang dikongsi membolehkan penipu log masuk sehingga ia ditukar dan sesi lama ditamatkan.",
        ),
        "never_share_otp": (
            "Jangan berikan OTP, PIN atau kata laluan anda kepada sesiapa lagi, walaupun mereka mengaku membantu memulihkan wang anda.",
            "Panggilan susulan sering menyamar sebagai pegawai pemulihan atau bank untuk mendapatkan set kod kedua.",
        ),
        "contain_link": (
            "Tutup halaman itu, jangan masukkan sebarang maklumat dan jangan buka semula pautan tersebut. Jika anda ada menaip sesuatu, beritahu saya jenisnya (jangan nyatakan nilai sebenar) dan anggap ia sebagai kelayakan yang telah dikongsi.",
            "Membuka pautan sahaja berisiko lebih rendah daripada memasukkan data, tetapi ia boleh membawa kepada halaman log masuk palsu atau muat turun.",
        ),
        "scan_device": (
            "Jalankan imbasan dengan aplikasi keselamatan yang terkini dan semak aplikasi serta muat turun yang baru dipasang untuk apa-apa yang tidak anda kenali.",
            "Halaman berniat jahat boleh cuba memuat turun perisian tanpa disedari.",
        ),
        "clean_device": (
            "Semak aplikasi yang dipasang serta kebenaran pentadbir peranti dan kebolehcapaian, dan buang apa-apa yang tidak anda pasang dengan sengaja. Jika tidak boleh dibuang, sandarkan foto/dokumen anda dan tetapkan semula peranti kepada tetapan kilang.",
            "Sesetengah aplikasi berniat jahat menyembunyikan diri atau dipasang semula, jadi pembuangan perlu disemak selepas itu.",
        ),
        "identity_watch": (
            "Maklumkan bank anda, perhatikan akaun, pinjaman atau pendaftaran SIM baharu atas nama anda, dan semak laporan kredit anda (contohnya CCRIS melalui Bank Negara Malaysia, atau biro kredit yang anda percayai) untuk entri yang tidak anda kenali.",
            "Salinan IC atau selfie boleh digunakan untuk membuka akaun atau lulus semakan identiti.",
        ),
        "preserve_evidence": (
            "Sebelum menyekat atau memadam apa-apa, ambil tangkapan skrin sembang, mesej, nombor pemanggil, alamat laman web dan resit pembayaran, dan catat tarikh, masa, jumlah serta butiran akaun penerima. Jangan membalas atau berhadapan dengan penipu.",
            "Bank dan polis memerlukannya untuk menjejak dan melaporkan kes, dan ia mudah hilang apabila sembang dipadam.",
        ),
        "police_report": (
            "Buat laporan polis dan simpan nombor laporan serta salinan resit anda.",
            "Laporan polis biasanya diperlukan untuk siasatan bank.",
        ),
        "no_more_payments": (
            "Jangan hantar lagi wang, termasuk 'yuran', 'cukai' atau 'caj pelepasan' untuk mendapatkan wang anda semula.",
            "Penipuan pemulihan menyasarkan orang yang sudah ditipu.",
        ),
        "reject_recovery_offer": (
            "Jangan bayar sesiapa yang menawarkan untuk mendapatkan semula wang anda dengan bayaran, dan jangan kongsi butiran bank atau pengenalan anda dengan mereka. Sahkan sebarang bantuan pemulihan hanya melalui bank anda atau NSRC (997) menggunakan butiran hubungan yang anda cari sendiri.",
            "Penipuan pemulihan menyasarkan orang yang sudah kehilangan wang; saluran pelaporan rasmi tidak memerlukan anda membayar untuk laporan diterima.",
        ),
        "report_nfcc": (
            "Laporkan juga insiden ini di laman web NFCC yang disenaraikan di bawah, dan beritahu ahli keluarga atau rakan yang dipercayai supaya anda tidak menghadapinya seorang diri.",
            "Laporan membantu pihak berkuasa mengaitkan kes dan memberi amaran kepada orang lain.",
        ),
        "check_recipient": (
            "Secara pilihan, semak akaun penerima sendiri di portal rasmi Semak Mule.",
            "Ia cara pantas untuk melihat sama ada akaun itu pernah dilaporkan; ia tidak membuktikan atau menafikan penipuan.",
        ),
    },
    "call_bank_end": {True: " jika ada wang yang keluar dari akaun anda.", False: "."},
}

_ZH: dict[str, Any] = {
    "ui": {
        "title": "### 诈骗应对计划：{headline}",
        "severity_line": (
            "**严重程度：{severity}。** 这是根据您所述内容提供的指引，并非已证实的诈骗结论。"
            "我没有联系任何人，也没有代您采取任何行动；每一步都需要您自己完成。"
        ),
        "tier_now": "现在就做",
        "tier_today": "今天稍后",
        "tier_follow_up": "接下来几天",
        "why": "原因",
        "conditional": "如果适用：",
        "channels": "官方渠道",
        "questions": "请告诉我（不要提供密码、验证码或账号），以便我完善此计划",
        "untrusted": (
            "请不要使用骗子或可疑信息中的任何电话号码、链接或指示，包括贴在此处的内容。"
            "请只使用上面列出的渠道。"
        ),
        "analysis_note": "信息分析仅用于判断应保持多谨慎，无法证实您做了什么。",
        "urgent_critical": (
            "请立即行动：如果钱已从您的账户转出，或您透露了验证码或银行信息，请马上致电银行官方"
            "防诈骗热线（使用银行卡或官方App上的号码）和 NSRC 997。完整步骤如下。"
        ),
        "urgent_generic": "我正在根据您所述的情况准备应对步骤。",
    },
    "severity": {"precautionary": "预防性", "moderate": "中等", "high": "高", "critical": "危急"},
    "headlines": {
        "money_sent": "您的资金可能已转出账户",
        "financial_credentials": "银行信息或一次性验证码可能已泄露",
        "other_credentials": "密码或登录信息可能已泄露",
        "data_entered_on_site": "您可能在虚假页面输入了资料",
        "remote_access": "有人可能已能远程控制您的设备",
        "app_installed": "您的设备上可能安装了可疑应用",
        "identity_documents": "您的身份证件可能已泄露",
        "link_interaction": "您打开了可疑链接",
        "unspecified_victim": "您觉得自己可能被骗了",
        "recovery_scam": "有人以收费方式提出帮您追回被骗资金",
    },
    "channels": {
        "bank": ("银行官方防诈骗热线", "使用银行卡背面或银行官方App内的号码"),
        "nsrc": (None, "拨打 997"),
        "police": (None, "到警局报案并保留报案编号"),
        "nfcc": (None, None),
        "semak_mule": (None, "自行打开 https://semakmule.rmp.gov.my/ 查询收款账户；不要把账号贴到聊天中"),
    },
    "questions": {
        "Did any money leave your account, and roughly when?": "是否有钱从您的账户转出？大约是什么时候？",
        "Did you share any OTP/TAC, PIN, card details or passwords?": "您是否透露过 OTP/TAC、PIN、银行卡信息或密码？",
        "Did you install an app or give anyone remote access to your device?": "您是否安装过应用或让别人远程访问您的设备？",
    },
    "steps": {
        "disconnect_device": (
            "关闭受影响设备的 Wi-Fi 和移动数据，并在“设置”中关闭或卸载远程控制软件及不认识的应用。如有可能，请用另一台干净的设备或另一条电话线完成接下来的步骤。",
            "断开连接可防止他人查看您的屏幕或在您处理期间批准交易。",
        ),
        "call_bank": (
            "致电银行官方防诈骗热线（使用银行卡背面或银行官方App内的号码，不要用任何信息里的号码），请银行冻结您的银行卡/网银，并阻止或追查这笔转账{end}",
            "时间很重要：银行有时只能在转账刚发生后不久拦截或追查。",
        ),
        "call_nsrc": (
            "拨打 997 向国家诈骗应对中心 (NSRC) 报案（马来西亚）。",
            "NSRC 会与银行协调处理疑似诈骗转账。",
        ),
        "change_credentials": (
            "通过官方网站或App（自己输入网址）更改已泄露的密码，先从电邮和银行账户开始。退出所有其他设备和登录状态，并开启多重验证。其他使用相同密码的账户也要更改。",
            "骗子拿到密码或验证码后，在您更改密码并注销旧登录之前都可能登录您的账户。",
        ),
        "never_share_otp": (
            "不要再把 OTP、PIN 或密码告诉任何人，即使对方自称在帮您追回钱款。",
            "后续来电常冒充追讨人员或银行职员，以骗取第二轮验证码。",
        ),
        "contain_link": (
            "关闭该页面，不要输入任何资料，也不要再次打开该链接。如果您输入过任何内容，请告诉我是哪一类（不要说出具体内容），并按资料已泄露处理。",
            "仅打开链接的风险低于输入资料，但仍可能引向虚假登录页面或下载。",
        ),
        "scan_device": (
            "用最新的安全软件扫描设备，并检查最近安装的应用和下载内容，看是否有不认识的项目。",
            "恶意页面可能在您不知情时尝试下载软件。",
        ),
        "clean_device": (
            "检查已安装的应用以及设备管理员和无障碍权限，移除任何不是您主动安装的项目。如果无法移除，请先备份照片和文件，再将设备恢复出厂设置。",
            "部分恶意应用会隐藏自己或自动重新安装，所以移除后需要再次检查。",
        ),
        "identity_watch": (
            "通知您的银行，留意是否有以您名义开立的新账户、贷款或SIM卡登记，并查看您的信用报告（例如通过马来西亚国家银行的 CCRIS，或您信任的信用机构），看是否有不认识的记录。",
            "身份证或自拍照可能被用来开户或通过身份验证。",
        ),
        "preserve_evidence": (
            "在拉黑或删除任何内容之前，先为聊天记录、信息、来电号码、网址和付款收据截图，并记下日期、时间、金额和收款账户资料。不要回复或与骗子对质。",
            "银行和警方需要这些资料来追查和立案，而聊天记录一旦删除就很容易丢失。",
        ),
        "police_report": (
            "向警方报案，并保留报案编号和收据副本。",
            "银行调查通常需要警方报案记录。",
        ),
        "no_more_payments": (
            "不要再汇出任何款项，包括为了“取回钱”而要求的“手续费”“税款”或“解冻费”。",
            "追讨诈骗专门针对已经被骗的人。",
        ),
        "reject_recovery_offer": (
            "不要向任何声称收费帮您追回钱款的人付款，也不要向他们提供银行或身份资料。任何追讨协助都只能通过您的银行或 NSRC (997)，并使用您自己查到的联系方式来核实。",
            "追讨诈骗专门针对已经损失钱财的人；官方报案渠道不需要您付费才受理报案。",
        ),
        "report_nfcc": (
            "也请在下方列出的 NFCC 网站上报告此事，并告诉值得信任的家人或朋友，不要独自面对。",
            "报告有助于当局关联案件并提醒其他人。",
        ),
        "check_recipient": (
            "可自行到官方 Semak Mule 网站查询收款账户。",
            "这能快速了解该账户是否曾被举报；但不能证明或排除诈骗。",
        ),
    },
    "call_bank_end": {True: "（如果确实有钱转出）。", False: "。"},
}

_LANGS: dict[str, dict[str, Any]] = {"ms": _MS, "zh": _ZH}


class Translator:
    """Look up localised text, falling back to English for anything missing."""

    def __init__(self, language: str) -> None:
        self.language = language if language in _LANGS else "en"
        self._data = _LANGS.get(self.language, {})

    def ui(self, key: str, **fmt: Any) -> str:
        text = self._data.get("ui", {}).get(key) or _EN_UI[key]
        return text.format(**fmt) if fmt else text

    def severity(self, severity: str) -> str:
        return self._data.get("severity", {}).get(severity, severity)

    def headline(self, kind: str, fallback: str) -> str:
        return self._data.get("headlines", {}).get(kind, fallback)

    def channel(self, key: str, name: str, how: str) -> tuple[str, str]:
        local_name, local_how = self._data.get("channels", {}).get(key, (None, None))
        return (local_name or name, local_how or how)

    def question(self, english: str) -> str:
        return self._data.get("questions", {}).get(english, english)

    def step(self, step_id: str, action: str, why: str, conditional: bool) -> tuple[str, str]:
        localized = self._data.get("steps", {}).get(step_id)
        if not localized:
            return action, why
        local_action, local_why = localized
        if "{end}" in local_action:
            local_action = local_action.replace(
                "{end}", self._data["call_bank_end"][bool(conditional)]
            )
        return local_action, local_why
