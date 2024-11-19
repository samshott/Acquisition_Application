# Check and install required packages
if (!require("pacman")) install.packages("pacman")
pacman::p_load(shiny, lidR, raster, shinythemes, shinyFiles, shinyBS, shinyjs)

# If you're having issues with choose.dir on Windows, uncomment these lines:
# if (.Platform$OS.type == "windows") {
#   if (!require("installr")) install.packages("installr")
#   if (!require("tcltk")) install.packages("tcltk")
# }

# Set maximum file size to 30GB
options(shiny.maxRequestSize = 30000*1024^2)

ui <- fluidPage(
  theme = shinytheme("flatly"),
  useShinyjs(),
  tags$style(HTML("
    .progress {
      margin-top: 15px;
    }
    .well {
      background-color: #f8f9fa;
    }
  ")),
  
  titlePanel("LiDAR Point Cloud to Ortho/Hillshade Converter"),
  
  sidebarLayout(
    sidebarPanel(
      # Input LAS/LAZ file with file size info
      fileInput("las_file", "Select LAS/LAZ file (max 30GB)",
                accept = c(".las", ".laz"),
                multiple = FALSE),
      
      # Output directory selection
      textInput("output_dir", "Output Directory (paste path)", value = "",
                placeholder = "C:/Users/YourName/Documents/LidarOutputs"),
      actionButton("browse_dir", "Open File Explorer"),
      tags$div(
        style = "color: #666; font-size: 0.8em; margin-top: 5px;",
        "Click 'Open File Explorer' to browse, then copy-paste the desired path above"
      ),
      
      hr(),
      
      # Resolution settings
      numericInput("resolution", "Resolution (meters)", 
                   value = 1,
                   min = 0.1,
                   max = 10,
                   step = 0.1),
      
      bsTooltip("resolution", 
                "Lower values give higher detail but take longer to process",
                placement = "right"),
      
      # Output options
      checkboxGroupInput("outputs", "Select outputs:",
                         choices = list(
                           "RGB Ortho" = "rgb",
                           "DSM" = "dsm",
                           "DSM Hillshade" = "hillshade",
                           "DTM" = "dtm",
                           "DTM Hillshade" = "dtm_hillshade",
                           "Intensity" = "intensity",
                           "Point Density" = "density"
                         ),
                         selected = c("rgb", "dsm", "hillshade")),
      
      # Hillshade parameters (if selected)
      conditionalPanel(
        condition = "input.outputs.includes('hillshade')",
        sliderInput("hill_angle", "Sun Angle", 
                    min = 0, max = 90, value = 45),
        sliderInput("hill_direction", "Sun Direction",
                    min = 0, max = 360, value = 315)
      ),
      
      hr(),
      
      # Memory usage warning
      tags$div(
        style = "color: #666; font-size: 0.8em; margin-bottom: 10px;",
        "Note: Large point clouds may require significant memory. Consider using a lower resolution for initial tests."
      ),
      
      # Process button
      actionButton("process", "Process Point Cloud",
                   class = "btn-primary btn-lg btn-block",
                   style = "margin-top: 25px;")
    ),
    
    mainPanel(
      tabsetPanel(
        tabPanel("Log",
                 verbatimTextOutput("log")),
        tabPanel("Help",
                 tags$div(
                   style = "padding: 15px;",
                   tags$h4("Instructions:"),
                   tags$ol(
                     tags$li("Select your LAS/LAZ file (up to 30GB)"),
                     tags$li("Choose an output directory"),
                     tags$li("Set the desired resolution (lower = more detailed but slower)"),
                     tags$li("Select the outputs you want to generate"),
                     tags$li("If using hillshade, adjust sun angle and direction as needed"),
                     tags$li("Click 'Process Point Cloud' to begin")
                   ),
                   tags$h4("Tips:"),
                   tags$ul(
                     tags$li("Start with a higher resolution (e.g., 2m) for faster processing during initial tests"),
                     tags$li("Check the Log tab for processing status and any errors"),
                     tags$li("Large point clouds may take several minutes to process")
                   )
                 ))
      )
    )
  )
)

server <- function(input, output, session) {
  values <- reactiveValues(
    las = NULL,
    output_dir = NULL,
    processing = FALSE,
    log_messages = character(0)
  )
  
  # Directory selection button using shinyFiles
  observeEvent(input$browse_dir, {
    if (Sys.info()["sysname"] == "Windows") {
      # For Windows
      shell.exec("explorer")  # Opens File Explorer
    } else if (Sys.info()["sysname"] == "Darwin") {
      # For Mac
      system("open .")  # Opens Finder
    } else {
      # For Linux
      system("xdg-open .")  # Opens file manager
    }
  })
  
  # Add log message function
  add_log <- function(message) {
    values$log_messages <- c(values$log_messages, 
                             paste(format(Sys.time(), "%H:%M:%S"), "-", message))
  }
  
  # Update log output
  output$log <- renderPrint({
    cat(paste(values$log_messages, collapse = "\n"))
  })
  
  # Process point cloud when button is clicked
  observeEvent(input$process, {
    req(input$las_file, input$output_dir)
    
    # Disable process button
    disable("process")
    values$processing <- TRUE
    
    # Create progress object
    withProgress(message = 'Processing point cloud', value = 0, {
      
      # Wrap processing in try-catch
      tryCatch({
        # Read LAS file
        add_log("Reading LAS file...")
        incProgress(0.1, detail = "Reading LAS file")
        las <- readLAS(input$las_file$datapath)
        
        # Create output directory if it doesn't exist
        if (!dir.exists(input$output_dir)) {
          dir.create(input$output_dir, recursive = TRUE)
        }
        
        # Get base filename without extension once
        base_name <- tools::file_path_sans_ext(input$las_file$name)
        
        # Process based on selected outputs
        if ("dtm" %in% input$outputs || "dtm_hillshade" %in% input$outputs) {
          add_log("Classifying ground points...")
          # Classify ground points
          las_ground <- classify_ground(las, algorithm = csf())
          
          add_log("Creating DTM...")
          incProgress(0.2, detail = "Creating DTM")
          dtm <- grid_terrain(las_ground, 
                              res = input$resolution,
                              algorithm = tin())
          
          if ("dtm" %in% input$outputs) {
            writeRaster(dtm,
                        file.path(input$output_dir, paste0(base_name, "_dtm.tif")),
                        overwrite = TRUE)
          }
          
          if ("dtm_hillshade" %in% input$outputs) {
            add_log("Creating DTM hillshade...")
            slope_dtm <- terrain(dtm, opt = "slope")
            aspect_dtm <- terrain(dtm, opt = "aspect")
            hillshade_dtm <- hillShade(slope_dtm, aspect_dtm,
                                       angle = input$hill_angle,
                                       direction = input$hill_direction)
            
            writeRaster(hillshade_dtm,
                        file.path(input$output_dir, paste0(base_name, "_dtm_hillshade.tif")),
                        overwrite = TRUE)
          }
        }
        
        if ("dsm" %in% input$outputs || "hillshade" %in% input$outputs) {
          add_log("Creating DSM...")
          incProgress(0.2, detail = "Creating DSM")
          dsm <- grid_canopy(las, 
                             res = input$resolution,
                             algorithm = p2r())
          
          if ("dsm" %in% input$outputs) {
            writeRaster(dsm, 
                        file.path(input$output_dir, paste0(base_name, "_dsm.tif")),
                        overwrite = TRUE)
          }
          
          if ("hillshade" %in% input$outputs) {
            add_log("Creating DSM hillshade...")
            slope <- terrain(dsm, opt = "slope")
            aspect <- terrain(dsm, opt = "aspect")
            hillshade <- hillShade(slope, aspect,
                                   angle = input$hill_angle,
                                   direction = input$hill_direction)
            
            writeRaster(hillshade,
                        file.path(input$output_dir, paste0(base_name, "_dsm_hillshade.tif")),
                        overwrite = TRUE)
          }
        }
        
        if ("rgb" %in% input$outputs) {
          add_log("Creating RGB ortho...")
          incProgress(0.2, detail = "Creating RGB ortho")
          
          # Check if RGB values exist
          if (all(c("R", "G", "B") %in% names(las@data))) {
            # Create separate rasters for R, G, B using highest points
            r_raster <- grid_metrics(las, ~R[which.max(Z)], res = input$resolution)
            g_raster <- grid_metrics(las, ~G[which.max(Z)], res = input$resolution)
            b_raster <- grid_metrics(las, ~B[which.max(Z)], res = input$resolution)
            
            # Stack the RGB rasters
            ortho_rgb <- stack(r_raster, g_raster, b_raster)
            names(ortho_rgb) <- c("R", "G", "B")
            
            writeRaster(ortho_rgb,
                        file.path(input$output_dir, paste0(base_name, "_rgb.tif")),
                        overwrite = TRUE)
          } else {
            add_log("Warning: No RGB values found in point cloud")
          }
        }
        
        if ("hillshade" %in% input$outputs) {
          add_log("Creating hillshade...")
          incProgress(0.2, detail = "Creating hillshade")
          
          if (!exists("dsm")) {
            dsm <- grid_canopy(las, 
                               res = input$resolution,
                               algorithm = p2r())
          }
          
          slope <- terrain(dsm, opt = "slope")
          aspect <- terrain(dsm, opt = "aspect")
          hillshade <- hillShade(slope, aspect,
                                 angle = input$hill_angle,
                                 direction = input$hill_direction)
          
          writeRaster(hillshade,
                      file.path(input$output_dir, paste0(base_name, "_hillshade.tif")),
                      overwrite = TRUE)
        }
        
        if ("intensity" %in% input$outputs) {
          add_log("Creating intensity ortho...")
          incProgress(0.2, detail = "Creating intensity ortho")
          
          ortho_intensity <- grid_metrics(las, ~mean(Intensity),
                                          res = input$resolution)
          writeRaster(ortho_intensity,
                      file.path(input$output_dir, paste0(base_name, "_intensity.tif")),
                      overwrite = TRUE)
        }
        
        if ("density" %in% input$outputs) {
          add_log("Creating point density raster...")
          incProgress(0.2, detail = "Creating density raster")
          
          density_raster <- grid_metrics(las, ~length(Z),
                                         res = input$resolution)
          writeRaster(density_raster,
                      file.path(input$output_dir, paste0(base_name, "_density.tif")),
                      overwrite = TRUE)
          
          add_log(paste("Average density:", round(mean(density_raster[], na.rm = TRUE), 2), "points per cell"))
          add_log(paste("Max density:", round(max(density_raster[], na.rm = TRUE), 2), "points per cell"))
        }
        
        incProgress(0.1, detail = "Finishing up")
        add_log("Processing complete!")
        
      }, error = function(e) {
        add_log(paste("Error:", e$message))
      }, finally = {
        # Re-enable process button
        enable("process")
        values$processing <- FALSE
      })
    })
  })
}

shinyApp(ui = ui, server = server)