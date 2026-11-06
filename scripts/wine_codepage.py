"""Wine reg.exe OEM output, using unxed/localecp's Unix locale algorithm.

Source: https://github.com/unxed/localecp/blob/43b67e27774605be8bf9783de6f5f793a0d8ab01/localecp.go
See localecp.LICENSE for the table's BSD-3-Clause license.
Python has native codecs for the OEM pages that Go's charmap approximates.
"""
import os

OEM_LOCALES = {
    'cp850': 'af_ZA ast_ES br_FR ca_ES kw_GB cy_GB da_DK de_AT de_LI de_LU de_CH de_DE en_AU en_CA en_GB en_IE en_JM en_BZ en_TT en_NZ es_PA es_BO es_CR es_DO es_SV es_EC es_GT es_HN es_NI es_CL es_MX es_ES es_CO es_PE es_AR es_PR es_VE es_UY es_PY eu_ES fi_FI fo_FO fr_FR fr_BE fr_CA fr_LU fr_MC fr_CH gd_GB gv_IM gl_ES id_ID is_IS it_IT it_CH ms_BN ms_MY nl_BE nl_NL nl_SR nn_NO nb_NO pt_BR pt_PT rm_CH sv_SE sv_FI wa_BE'.split(),
    'cp720': 'ar_SA ar_LB ar_EG ar_DZ ar_BH ar_IQ ar_JO ar_KW ar_LY ar_MA ar_OM ar_QA ar_SY ar_TN ar_AE ar_YE fa_IR ur_PK'.split(),
    'cp866': 'az_AZ@cyrillic be_BY bg_BG kk_KZ ky_KG mk_MK mn_MN ru_RU tt_RU uk_UA uz_UZ@cyrillic'.split(),
    'cp857': 'az_AZ tr_TR uz_UZ'.split(),
    'gbk': 'zh_CN zh_SG'.split(),
    'big5': 'zh_TW zh_HK zh_MO'.split(),
    'cp852': 'cs_CZ hr_HR hu_HU pl_PL ro_RO sk_SK sl_SI sq_AL sr_RS@latin'.split(),
    'cp737': 'el_GR'.split(),
    'cp437': 'en_PH en_ZA en_US en_ZW ga_IE iv_IV sw_KE'.split(),
    'cp775': 'et_EE lt_LT lv_LV'.split(),
    'cp862': 'he_IL'.split(),
    'cp932': 'ja_JP'.split(),
    'cp949': 'ko_KR'.split(),
    'cp855': 'sr_RS'.split(),
    'cp874': 'th_TH'.split(),
    'cp1258': 'vi_VN'.split(),
}
OEM_BY_LOCALE = {loc: codec for codec, locales in OEM_LOCALES.items() for loc in locales}


def oem_codec(env=None):
    """LC_ALL > LC_CTYPE > LANG, drop charset suffix, default to CP437."""
    env = os.environ if env is None else env
    loc = env.get("LC_ALL") or env.get("LC_CTYPE") or env.get("LANG") or ""
    return OEM_BY_LOCALE.get(loc.split(".", 1)[0], "cp437")


def decode_stdout(data, env=None):
    # reg.exe uses GetOEMCP even when the host locale says UTF-8.
    return data.decode(oem_codec(env), errors="replace")


def decode_stderr(data, env=None):
    # Wine's Unix diagnostics use UTF-8; Windows diagnostics may use OEM.
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return decode_stdout(data, env)
