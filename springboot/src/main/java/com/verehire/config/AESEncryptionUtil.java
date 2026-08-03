package com.verehire.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

@Component
public class AESEncryptionUtil {

    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH = 12;
    private static final int GCM_TAG_LENGTH = 128;

    private final SecretKeySpec secretKey;

    public AESEncryptionUtil(@Value("${app.encryption.key}") String encryptionKeyStr) {
        if (encryptionKeyStr == null || encryptionKeyStr.isBlank()) {
            throw new IllegalArgumentException("APP_ENCRYPTION_KEY must be provided via environment variables.");
        }
        
        // Ensure key is 32 bytes (256-bit)
        byte[] keyBytes = encryptionKeyStr.getBytes(StandardCharsets.UTF_8);
        byte[] finalKey = new byte[32];
        System.arraycopy(keyBytes, 0, finalKey, 0, Math.min(keyBytes.length, 32));
        
        this.secretKey = new SecretKeySpec(finalKey, "AES");
    }

    public String encrypt(String plainText) {
        if (plainText == null || plainText.isEmpty()) {
            return plainText;
        }
        try {
            byte[] iv = new byte[GCM_IV_LENGTH];
            new SecureRandom().nextBytes(iv);

            Cipher cipher = Cipher.getInstance(ALGORITHM);
            GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, gcmParameterSpec);

            byte[] cipherText = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));

            byte[] message = new byte[GCM_IV_LENGTH + cipherText.length];
            System.arraycopy(iv, 0, message, 0, GCM_IV_LENGTH);
            System.arraycopy(cipherText, 0, message, GCM_IV_LENGTH, cipherText.length);

            return Base64.getEncoder().encodeToString(message);
        } catch (Exception e) {
            throw new RuntimeException("Error while encrypting data", e);
        }
    }

    public String decrypt(String cipherTextBase64) {
        if (cipherTextBase64 == null || cipherTextBase64.isEmpty()) {
            return cipherTextBase64;
        }
        try {
            byte[] message = Base64.getDecoder().decode(cipherTextBase64);

            if (message.length < GCM_IV_LENGTH) {
                throw new IllegalArgumentException("Invalid cipher text");
            }

            byte[] iv = new byte[GCM_IV_LENGTH];
            System.arraycopy(message, 0, iv, 0, GCM_IV_LENGTH);

            byte[] cipherText = new byte[message.length - GCM_IV_LENGTH];
            System.arraycopy(message, GCM_IV_LENGTH, cipherText, 0, cipherText.length);

            Cipher cipher = Cipher.getInstance(ALGORITHM);
            GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, gcmParameterSpec);

            return new String(cipher.doFinal(cipherText), StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new RuntimeException("Error while decrypting data", e);
        }
    }
}
