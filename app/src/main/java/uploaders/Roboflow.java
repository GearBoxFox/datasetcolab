package uploaders;

import utils.Utils;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.auth.oauth2.GoogleCredentials;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseAuthException;
import com.google.firebase.auth.FirebaseToken;
import io.javalin.Javalin;
import io.javalin.community.ssl.SSLPlugin;
import io.javalin.http.UploadedFile;
import java.io.*;
import java.util.*;
import java.util.ArrayList;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

import java.util.HashSet;
import java.util.Set;
import java.text.SimpleDateFormat;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;
import org.json.simple.JSONArray;
import java.util.concurrent.CompletableFuture;

import io.javalin.Javalin;
import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

public class Roboflow {

    private Utils utils = new Utils();
    public Set<String> classes = new HashSet<>();
    public ArrayList<Integer> classAmounts = new ArrayList();

    public String upload(String folderName, String roboflowUrl, String uid) {
        String apiKey = readApiKeyFromFile("roboflow.txt");

        String workspace = getWorkspaceFromUrl(roboflowUrl);
        String project = getProjectFromUrl(roboflowUrl);
        System.out.println(workspace);
        System.out.println(project);

        String apiUrl = "https://api.roboflow.com/" + workspace;
        String apiKeyParam = "?api_key=" + apiKey;


        String versionsJSONString = utils.executeCommand("curl https://api.roboflow.com/" + workspace + "/" + project + "?api_key=" + apiKey);
        String latestVersionId = parseLatestVersionId(versionsJSONString);
        String versionJSON = utils.executeCommand("curl https://api.roboflow.com/" + latestVersionId + "/coco?api_key=" + apiKey);
        System.out.println(versionJSON);
        String exportLink = parseExportLink(versionJSON);

        if (exportLink == null) {
            int tries = 0;
            while (exportLink == null && tries < 5) {
                versionsJSONString = utils.executeCommand("curl https://api.roboflow.com/" + workspace + "/" + project + "?api_key=" + apiKey);
                latestVersionId = parseLatestVersionId(versionsJSONString);
                versionJSON = utils.executeCommand("curl https://api.roboflow.com/" + latestVersionId + "/coco?api_key=" + apiKey);
                exportLink = parseExportLink(versionJSON);

                tries++;
            }
        }

        try {
            JSONParser parser = new JSONParser();
            JSONObject versionsJSON = (JSONObject) parser.parse(versionsJSONString);

            JSONObject projectJSON = (JSONObject) versionsJSON.get("project");
            JSONObject classesJSON = (JSONObject) projectJSON.get("classes");

            for (Object className : classesJSON.keySet()) {
                classes.add((String) className);
            }

            return exportLink;
        } catch (org.json.simple.parser.ParseException e) {
            e.printStackTrace();
            return null;
        }
    }

    public void postUpload(String uid, String folderName, String exportLink) {
        utils.executeCommand("mkdir -p upload/" + uid + "/" + folderName);
        utils.executeCommand("wget --user-agent='Mozilla/5.0' -O upload/" + uid + "/" + folderName + "/dataset.zip " + exportLink);

        if (utils.getLastExitCode() == 0) {
            utils.executeCommand("unzip upload/" + uid + "/" + folderName + "/dataset.zip -d upload/" + uid + "/" + folderName);
            utils.executeCommand("rm upload/" + uid + "/" + folderName + "/dataset.zip");
        } else {
            System.err.println("Download failed. Skipping unzip.");
        }
    }

    private String readApiKeyFromFile(String filePath) {
        try {
            String content = Files.readString(Path.of("important.json"));
            JSONObject jsonObject = new JSONObject((Map <?,?> ) new JSONParser().parse(content));
            return (String) jsonObject.get("ROBOFLOW_API");
        } catch (IOException | ParseException e) {
            e.printStackTrace();
            return null;
        }
    }

    private String parseLatestVersionId(String versionsJson) {
        JsonObject json = JsonParser.parseString(versionsJson).getAsJsonObject();
        JsonArray versionsArray = json.getAsJsonArray("versions");
        JsonObject latestVersion = versionsArray.get(0).getAsJsonObject();
        return latestVersion.get("id").getAsString();
    }

    private String parseExportLink(String versionJson) {
        JsonObject json = JsonParser.parseString(versionJson).getAsJsonObject();
        JsonObject export = json.getAsJsonObject("export");
        return export.get("link").getAsString();
    }
    
    public String getWorkspaceFromUrl(String roboflowUrl) {
        String[] parts = roboflowUrl.split("/");
        int startIndex = roboflowUrl.startsWith("https://") || roboflowUrl.startsWith("http://") ? 3 : 2;
        return parts[startIndex];
    }

    public String getProjectFromUrl(String roboflowUrl) {
        String[] parts = roboflowUrl.split("/");
        int startIndex = roboflowUrl.startsWith("https://") || roboflowUrl.startsWith("http://") ? 4 : 3;
        return parts[startIndex];
    }
}

