package com.one.mini.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
public class FileService {
    @Value("${file.upload.path:./uploads}")
    private String uploadPath;

    @Value("${file.upload.allowed-extensions:jpg,jpeg,png,gif,webp}")
    private String allowedExtensions;

    public String uploadFile(MultipartFile file) throws IOException {
        if (file.isEmpty()) {
            throw new IllegalArgumentException("文件不能为空");
        }

        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || originalFilename.isEmpty()) {
            throw new IllegalArgumentException("文件名无效");
        }

        String extension = getFileExtension(originalFilename);
        if (!isAllowedExtension(extension)) {
            throw new IllegalArgumentException("不支持的文件格式: " + extension);
        }

        String newFilename = UUID.randomUUID().toString() + "." + extension;
        Path uploadDir = Paths.get(uploadPath);
        if (!Files.exists(uploadDir)) {
            Files.createDirectories(uploadDir);
        }

        Path filePath = uploadDir.resolve(newFilename);
        file.transferTo(filePath.toFile());
        log.info("File uploaded: {}", newFilename);

        return "/api/files/" + newFilename;
    }

    public byte[] getFile(String filename) throws IOException {
        Path filePath = Paths.get(uploadPath).resolve(filename);
        if (!Files.exists(filePath)) {
            return null;
        }
        return Files.readAllBytes(filePath);
    }

    public boolean deleteFile(String filename) {
        try {
            Path filePath = Paths.get(uploadPath).resolve(filename);
            return Files.deleteIfExists(filePath);
        } catch (IOException e) {
            log.error("Failed to delete file: {}", e.getMessage());
            return false;
        }
    }

    private String getFileExtension(String filename) {
        int dotIndex = filename.lastIndexOf('.');
        return dotIndex > 0 ? filename.substring(dotIndex + 1).toLowerCase() : "";
    }

    private boolean isAllowedExtension(String extension) {
        List<String> allowed = List.of(allowedExtensions.split(","));
        return allowed.contains(extension.toLowerCase());
    }
}