#!/usr/bin/env python3
"""Builds sub.txt (free public V2Ray configs, quick-tested). Runs on GitHub Actions every few hours."""
import base64, json, random, re, socket, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

SOURCES = [
    'https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub1.txt',
    'https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub2.txt',
    'https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub3.txt',
    'https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt',
    'https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/trojan.txt',
    'https://raw.githubusercontent.com/nyeinkokoaung404/V2ray-Configs/main/Sub1.txt',
    'https://raw.githubusercontent.com/hamedcode/port-based-v2ray-configs/main/sub/top100.txt',
    'https://raw.githubusercontent.com/hamedcode/port-based-v2ray-configs/main/sub/vless.txt',
    'https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt',
    'https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt',
    'https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt',
    'https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/master/sub/proxies.txt',
    'https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix',
    'https://raw.githubusercontent.com/itsyebekhe/PSG/main/subscriptions/xray/normal/mix',
    'https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/splitted/vless',
    'https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt',
    'https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/main/all_configs.txt',
    'https://raw.githubusercontent.com/10ium/V2Hub/main/merged_base64',
]
TOP = 200          # configs kept in sub.txt
MAX_TEST = 6000    # random sample size for the TCP test
TIMEOUT = 3.0      # seconds per connect
PER_HOST = 3

def fetch(u):
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode('utf-8', 'ignore')
    except Exception:
        return ''

def b64(s):
    s = s.strip().replace('-', '+').replace('_', '/')
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8', 'ignore')
    except Exception:
        return ''

def links(text):
    if '://' not in text:
        text = b64(re.sub(r'\s', '', text))
    out = []
    for l in re.split(r'[\r\n]+', text):
        l = l.strip()
        if re.match(r'^(vless|vmess|trojan|ss)://', l):
            out.append(l)
    return out

def info(link):
    """returns (host, port, security) or None"""
    try:
        if link.startswith('vmess://'):
            j = json.loads(b64(link[8:]))
            return str(j['add']), int(j['port']), ('tls' if str(j.get('tls')) == 'tls' else 'none')
        if link.startswith(('vless://', 'trojan://')):
            u = urllib.parse.urlsplit(link)
            q = urllib.parse.parse_qs(u.query)
            default = 'tls' if link.startswith('trojan') else 'none'
            sec = (q.get('security', [''])[0] or default).lower()
            if not u.hostname or not u.port:
                return None
            return u.hostname, u.port, sec
        if link.startswith('ss://'):
            body = link[5:].split('#')[0].split('?')[0]
            m = re.search(r'@(\[[^\]]+\]|[^:/?#@]+):(\d+)', body) or re.search(r'@(\[[^\]]+\]|[^:/?#@]+):(\d+)', b64(body))
            if m:
                return m.group(1).strip('[]'), int(m.group(2)), 'none'
    except Exception:
        pass
    return None

def tcp_ms(host, port):
    t = time.time()
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return int((time.time() - t) * 1000)
    except Exception:
        return None

def main():
    with ThreadPoolExecutor(12) as ex:
        texts = list(ex.map(fetch, SOURCES))
    allv = []
    for u, t in zip(SOURCES, texts):
        ls = links(t)
        print(f'{len(ls):6d}  {u}')
        allv += ls
    if not allv:
        print('nothing downloaded'); sys.exit(1)

    seen, cands = set(), []
    for l in allv:
        key = l.split('#')[0]
        if key in seen:
            continue
        seen.add(key)
        inf = info(l)
        if not inf:
            continue
        host, port, sec = inf
        if re.match(r'^(0\.|127\.|10\.|192\.168\.|localhost)', host) or not (0 < port < 65536):
            continue
        if not l.startswith('ss://') and sec not in ('tls', 'reality'):
            continue   # skip unencrypted transports
        cands.append((l, host, port))
    print('unique usable:', len(cands))
    random.shuffle(cands)
    cands = cands[:MAX_TEST]

    with ThreadPoolExecutor(200) as ex:
        res = list(ex.map(lambda c: tcp_ms(c[1], c[2]), cands))
    good = [(c, ms) for c, ms in zip(cands, res) if ms is not None]
    print('answered:', len(good))
    if len(good) < 10:
        print('too few, keeping old sub.txt'); sys.exit(1)

    per, kept = {}, []
    for (l, h, p), ms in sorted(good, key=lambda x: (x[0][2] != 443, x[1])):
        if per.get(h, 0) >= PER_HOST:
            continue
        per[h] = per.get(h, 0) + 1
        kept.append(l)
        if len(kept) >= TOP:
            break

    lines = []
    for i, l in enumerate(kept, 1):
        lines.append(l if l.startswith('vmess://') else f"{l.split('#')[0]}#Noor_{i:03d}")
    data = base64.b64encode('\n'.join(lines).encode()).decode()
    open('sub.txt', 'w').write(data)
    print('written sub.txt with', len(lines), 'configs')

if __name__ == '__main__':
    main()
