/*
 * This Java source file was generated by the Gradle 'init' task.
 */
package frcdatasetcolab;

import io.javalin.Javalin;
import io.javalin.util.FileUtil;
import io.javalin.http.UploadedFile;
import java.text.SimpleDateFormat;
import java.util.Date;
import io.javalin.community.ssl.SSLPlugin;

public class App {
    public static void main(String[] args) {
	Javalin app = Javalin.create(config -> {
            config.plugins.enableCors(cors -> {
                cors.add(corsConfig -> {
                    //replacement for enableCorsForAllOrigins()
                    corsConfig.anyHost();
                });
            });
	    config.plugins.register(new SSLPlugin(ssl->{
	    ssl.host = "10.0.0.142";
	    ssl.insecurePort=7070;
	    ssl.securePort=3433;
            ssl.pemFromPath("fullchain.pem", "privkey.pem");
    }));
        })
            .get("/", ctx -> ctx.result("Hello World"))
            .start();
        
        app.post("/upload", ctx -> {
            Date date = new Date();
            SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd_HH:mm");
            String formattedDate = dateFormat.format(date);
            ctx.uploadedFiles("files").forEach(uploadedFile ->
                FileUtil.streamToFile(uploadedFile.content(), "upload/" + formattedDate + '_' + uploadedFile.filename())); // uploadedFile.filename()
        });
    }
    
}
