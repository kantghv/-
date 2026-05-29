package com.kaet.yingxiao.yingxiao_ai_mobile

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class MainActivity : FlutterActivity() {
    private var pendingPickResult: MethodChannel.Result? = null
    private var pendingModelImportResult: MethodChannel.Result? = null
    private var pendingModelFileName: String = "model.bin"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            handleSecureCall(call, result)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == MODEL_IMPORT_REQUEST) {
            finishModelImport(resultCode, data)
            return
        }
        if (requestCode != PICK_MEDIA_REQUEST) {
            return
        }
        val result = pendingPickResult
        pendingPickResult = null
        if (result == null) {
            return
        }
        if (resultCode != Activity.RESULT_OK) {
            result.success(null)
            return
        }
        val uri: Uri? = data?.data
        if (uri == null) {
            result.success(null)
            return
        }
        val flags = data.flags and (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        try {
            contentResolver.takePersistableUriPermission(uri, flags and Intent.FLAG_GRANT_READ_URI_PERMISSION)
        } catch (_: Exception) {
            // Some providers do not grant persistable permissions. The URI can still be used for the current session.
        }
        result.success(uri.toString())
    }

    private fun handleSecureCall(call: MethodCall, result: MethodChannel.Result) {
        try {
            when (call.method) {
                "getPrefs" -> result.success(appPrefs().getString(PREFS_JSON, null))
                "setPrefs" -> {
                    val json = call.argument<String>("json") ?: "{}"
                    appPrefs().edit().putString(PREFS_JSON, json).apply()
                    result.success(null)
                }
                "getSecret" -> {
                    val key = call.argument<String>("key") ?: "apiToken"
                    result.success(getSecret(key))
                }
                "setSecret" -> {
                    val key = call.argument<String>("key") ?: "apiToken"
                    val value = call.argument<String>("value") ?: ""
                    if (value.isEmpty()) {
                        secretPrefs().edit().remove(key).apply()
                    } else {
                        secretPrefs().edit().putString(key, encrypt(value)).apply()
                    }
                    result.success(null)
                }
                "deleteSecret" -> {
                    val key = call.argument<String>("key") ?: "apiToken"
                    secretPrefs().edit().remove(key).apply()
                    result.success(null)
                }
                "pickMedia" -> pickMedia(call.argument<String>("kind") ?: "image", result)
                "importModelFile" -> importModelFile(call.argument<String>("fileName") ?: "model.bin", result)
                "getModelRoot" -> {
                    val modelDir = File(filesDir, "local_models")
                    if (!modelDir.exists()) {
                        modelDir.mkdirs()
                    }
                    result.success(modelDir.absolutePath)
                }
                else -> result.notImplemented()
            }
        } catch (error: Exception) {
            result.error("YINGXIAO_SECURE_ERROR", error.message, null)
        }
    }

    private fun pickMedia(kind: String, result: MethodChannel.Result) {
        if (pendingPickResult != null) {
            result.error("PICKER_BUSY", "A picker request is already running.", null)
            return
        }
        pendingPickResult = result
        val mimeType = when (kind) {
            "video" -> "video/*"
            "any" -> "*/*"
            else -> "image/*"
        }
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = mimeType
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
        }
        startActivityForResult(intent, PICK_MEDIA_REQUEST)
    }

    private fun importModelFile(fileName: String, result: MethodChannel.Result) {
        if (pendingModelImportResult != null || pendingPickResult != null) {
            result.error("PICKER_BUSY", "A picker request is already running.", null)
            return
        }
        pendingModelImportResult = result
        pendingModelFileName = sanitizeFileName(fileName)
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivityForResult(intent, MODEL_IMPORT_REQUEST)
    }

    private fun finishModelImport(resultCode: Int, data: Intent?) {
        val result = pendingModelImportResult
        pendingModelImportResult = null
        if (result == null) {
            return
        }
        if (resultCode != Activity.RESULT_OK) {
            result.success(null)
            return
        }
        val uri = data?.data
        if (uri == null) {
            result.success(null)
            return
        }
        try {
            val modelDir = File(filesDir, "local_models")
            if (!modelDir.exists()) {
                modelDir.mkdirs()
            }
            val target = File(modelDir, pendingModelFileName)
            contentResolver.openInputStream(uri).use { input ->
                if (input == null) {
                    result.error("MODEL_IMPORT_FAILED", "Cannot open selected model file.", null)
                    return
                }
                target.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
            result.success(target.absolutePath)
        } catch (error: Exception) {
            result.error("MODEL_IMPORT_FAILED", error.message, null)
        }
    }

    private fun sanitizeFileName(value: String): String {
        val cleaned = value.replace(Regex("[^A-Za-z0-9._-]"), "_").trim('_')
        return if (cleaned.isEmpty()) "model.bin" else cleaned
    }

    private fun appPrefs() = getSharedPreferences("yingxiao_mobile_private", Context.MODE_PRIVATE)

    private fun secretPrefs() = getSharedPreferences("yingxiao_mobile_secrets", Context.MODE_PRIVATE)

    private fun getSecret(key: String): String? {
        val encrypted = secretPrefs().getString(key, null) ?: return null
        return decrypt(encrypted)
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateSecretKey())
        val iv = cipher.iv
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        return "${Base64.encodeToString(iv, Base64.NO_WRAP)}:${Base64.encodeToString(encrypted, Base64.NO_WRAP)}"
    }

    private fun decrypt(value: String): String? {
        val pieces = value.split(":")
        if (pieces.size != 2) {
            return null
        }
        val iv = Base64.decode(pieces[0], Base64.NO_WRAP)
        val encrypted = Base64.decode(pieces[1], Base64.NO_WRAP)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, getOrCreateSecretKey(), GCMParameterSpec(128, iv))
        return String(cipher.doFinal(encrypted), Charsets.UTF_8)
    }

    private fun getOrCreateSecretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        val spec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true)
            .build()
        generator.init(spec)
        return generator.generateKey()
    }

    companion object {
        private const val CHANNEL = "yingxiao/mobile_secure"
        private const val PICK_MEDIA_REQUEST = 4102
        private const val MODEL_IMPORT_REQUEST = 4103
        private const val PREFS_JSON = "prefs_json"
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "yingxiao_mobile_api_secret"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
