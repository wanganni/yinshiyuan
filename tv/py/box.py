#!/usr/bin/env python3
import sys
import binascii
import re
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def pad_end(key):
    """将密钥或IV填充至16字节"""
    return (key + "0000000000000000")[:16]

def decrypt_cbc(data_hex):
    """模拟 FongMi Decoder.java 的 cbc 解密逻辑"""
    try:
        # 1. 将十六进制转换为字节并尝试解码为字符串以提取元数据
        full_bytes = binascii.unhexlify(data_hex)
        # 使用 latin-1 避免 utf-8 解码失败，因为密文部分不是合法的 utf-8
        decode_str = full_bytes.decode('latin-1').lower()
        
        # 2. 提取 Key (位于 $# 和 #$ 之间)
        try:
            start_idx = decode_str.index("$#") + 2
            end_idx = decode_str.index("#$")
            key_raw = decode_str[start_idx:end_idx]
            key = pad_end(key_raw).encode('utf-8')
        except ValueError:
            return "错误: 未能在数据中找到 AES 密钥标记 ($#...#$)"

        # 3. 提取 IV (最后 13 个字符)
        iv_raw = decode_str[-13:]
        iv = pad_end(iv_raw).encode('utf-8')

        # 4. 提取加密主体 (位于 2324 [#$的hex] 之后，倒数第 26 个字符之前)
        try:
            # 在原始 hex 串中查找 #$ (2324)
            content_start = data_hex.index("2324") + 4
            content_end = len(data_hex) - 26
            encrypted_hex = data_hex[content_start:content_end]
            encrypted_bytes = binascii.unhexlify(encrypted_hex)
        except ValueError:
            return "错误: 未能在十六进制数据中定位密文标记 (2324)"

        # 5. 执行 AES 解密
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        return f"AES 解密失败: {str(e)}"

def decrypt_base64(data):
    """模拟 FongMi Decoder.java 的 base64 解密逻辑"""
    try:
        # 正则匹配: 8位字母数字 + **
        match = re.search(r'[A-Za-z0-9]{8}\*\*', data)
        if match:
            # 提取匹配项后 10 个字符之后的内容
            start_pos = data.index(match.group()) + 10
            base64_content = data[start_pos:]
            return base64.b64decode(base64_content).decode('utf-8')
        return "错误: 未能在数据中找到 Base64 标记 (8位字符+**)"
    except Exception as e:
        return f"Base64 解密失败: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print("用法: python3 tvbox_decryptor.py <文件名>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        print(f"读取文件失败: {e}")
        sys.exit(1)

    # 识别加密类型
    if content.startswith("2423"):
        print("[*] 识别为 AES/CBC 加密格式 (2423开头)")
        # 移除所有空白字符（模拟 Java 的 replaceAll("\\s+", "")）
        cleaned_content = re.sub(r'\s+', '', content)
        result = decrypt_cbc(cleaned_content)
    elif "**" in content:
        print("[*] 识别为 Base64 加密格式 (**标记)")
        result = decrypt_base64(content)
    elif content.startswith("{") or content.startswith("["):
        print("[*] 数据似乎未加密")
        result = content
    else:
        print("[!] 未知的数据格式，尝试直接输出前 100 字符:")
        print(content[:100])
        sys.exit(1)

    print("\n--- 解密结果 ---")
    print(result)
    print("----------------")

if __name__ == "__main__":
    main()
