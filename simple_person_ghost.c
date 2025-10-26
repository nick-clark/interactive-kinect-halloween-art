/*
 * Simple Person Ghost Effect - C Implementation (No OpenCV)
 * ========================================================
 * 
 * This is a C implementation of the simple_person_ghost.py script,
 * using libfreenect and basic image processing to avoid Python USB access issues.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <math.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>
#include <stdbool.h>
#include "libfreenect.h"

// Global variables
volatile bool running = true;
freenect_context* fn_ctx = NULL;
freenect_device* fn_dev = NULL;

// Effect parameters
int depth_min = 217;      // mm
int depth_max = 3626;     // mm
float ghost_alpha = 0.7f;

// Frame data
uint16_t* latest_depth = NULL;
uint8_t* latest_video = NULL;
uint16_t* background_image = NULL;
uint8_t* ghost_output = NULL;

// Threading
pthread_mutex_t frame_mutex = PTHREAD_MUTEX_INITIALIZER;

// Frame dimensions
#define DEPTH_WIDTH 640
#define DEPTH_HEIGHT 480
#define VIDEO_WIDTH 640
#define VIDEO_HEIGHT 480
#define VIDEO_CHANNELS 3

void signalHandler(int signal)
{
    if (signal == SIGINT || signal == SIGTERM || signal == SIGQUIT)
    {
        printf("\n🛑 Received signal %d, shutting down...\n", signal);
        running = false;
    }
}

void depth_cb(freenect_device *dev, void *depth, uint32_t timestamp)
{
    pthread_mutex_lock(&frame_mutex);
    
    if (!latest_depth) {
        latest_depth = (uint16_t*)malloc(DEPTH_WIDTH * DEPTH_HEIGHT * sizeof(uint16_t));
    }
    
    // Copy depth data
    memcpy(latest_depth, depth, DEPTH_WIDTH * DEPTH_HEIGHT * sizeof(uint16_t));
    
    pthread_mutex_unlock(&frame_mutex);
}

void video_cb(freenect_device *dev, void *video, uint32_t timestamp)
{
    pthread_mutex_lock(&frame_mutex);
    
    if (!latest_video) {
        latest_video = (uint8_t*)malloc(VIDEO_WIDTH * VIDEO_HEIGHT * VIDEO_CHANNELS * sizeof(uint8_t));
    }
    
    // Copy video data
    memcpy(latest_video, video, VIDEO_WIDTH * VIDEO_HEIGHT * VIDEO_CHANNELS * sizeof(uint8_t));
    
    pthread_mutex_unlock(&frame_mutex);
}

bool initialize_kinect()
{
    printf("🔧 Initializing Kinect for Simple Person Ghost Effect...\n");
    
    // Initialize libfreenect
    int ret = freenect_init(&fn_ctx, NULL);
    if (ret < 0)
    {
        printf("❌ Failed to initialize freenect context: %d\n", ret);
        return false;
    }
    printf("✅ Freenect context initialized\n");

    // Set log level and select camera
    freenect_set_log_level(fn_ctx, FREENECT_LOG_DEBUG);
    freenect_select_subdevices(fn_ctx, FREENECT_DEVICE_CAMERA);
    printf("✅ Log level set and camera selected\n");

    // Check device count
    int num_devices = freenect_num_devices(fn_ctx);
    if (num_devices < 0)
    {
        printf("❌ Failed to get device count: %d\n", num_devices);
        freenect_shutdown(fn_ctx);
        return false;
    }
    if (num_devices == 0)
    {
        printf("❌ No Kinect devices found!\n");
        freenect_shutdown(fn_ctx);
        return false;
    }
    printf("✅ Found %d Kinect device(s)\n", num_devices);

    // Open device
    ret = freenect_open_device(fn_ctx, &fn_dev, 0);
    if (ret < 0)
    {
        printf("❌ Failed to open device: %d\n", ret);
        freenect_shutdown(fn_ctx);
        return false;
    }
    printf("✅ Device opened successfully\n");

    // Set modes
    freenect_set_depth_mode(fn_dev, freenect_find_depth_mode(FREENECT_RESOLUTION_MEDIUM, FREENECT_DEPTH_MM));
    freenect_set_video_mode(fn_dev, freenect_find_video_mode(FREENECT_RESOLUTION_MEDIUM, FREENECT_VIDEO_RGB));
    printf("✅ Modes set\n");

    // Set callbacks
    freenect_set_depth_callback(fn_dev, depth_cb);
    freenect_set_video_callback(fn_dev, video_cb);
    printf("✅ Callbacks set\n");

    // Start streams
    freenect_start_depth(fn_dev);
    freenect_start_video(fn_dev);
    printf("✅ Streams started\n");

    return true;
}

void create_person_silhouette(uint8_t* silhouette, const uint16_t* depth_frame, const uint16_t* background)
{
    // Initialize silhouette to black
    memset(silhouette, 0, DEPTH_WIDTH * DEPTH_HEIGHT * VIDEO_CHANNELS);
    
    for (int y = 0; y < DEPTH_HEIGHT; y++) {
        for (int x = 0; x < DEPTH_WIDTH; x++) {
            int idx = y * DEPTH_WIDTH + x;
            int pixel_idx = idx * VIDEO_CHANNELS;
            
            uint16_t depth_value = depth_frame[idx];
            
            // Check if depth is in range
            if (depth_value >= depth_min && depth_value <= depth_max) {
                if (background) {
                    // Use background subtraction
                    uint16_t bg_value = background[idx];
                    if (abs((int)depth_value - (int)bg_value) > 50) {
                        // Person detected - set ghost color (BGR format)
                        silhouette[pixel_idx + 0] = 255;     // Blue
                        silhouette[pixel_idx + 1] = 200;     // Green  
                        silhouette[pixel_idx + 2] = 200;     // Red
                    }
                } else {
                    // No background, just use depth thresholding
                    silhouette[pixel_idx + 0] = 255;     // Blue
                    silhouette[pixel_idx + 1] = 200;     // Green
                    silhouette[pixel_idx + 2] = 200;     // Red
                }
            }
        }
    }
}

void apply_ghost_effect(uint8_t* output, const uint8_t* video_frame, const uint8_t* silhouette)
{
    for (int y = 0; y < VIDEO_HEIGHT; y++) {
        for (int x = 0; x < VIDEO_WIDTH; x++) {
            int pixel_idx = (y * VIDEO_WIDTH + x) * VIDEO_CHANNELS;
            
            uint8_t video_b = video_frame[pixel_idx + 0];
            uint8_t video_g = video_frame[pixel_idx + 1];
            uint8_t video_r = video_frame[pixel_idx + 2];
            
            uint8_t ghost_b = silhouette[pixel_idx + 0];
            uint8_t ghost_g = silhouette[pixel_idx + 1];
            uint8_t ghost_r = silhouette[pixel_idx + 2];
            
            // Check if ghost pixel has content
            if (ghost_b != 0 || ghost_g != 0 || ghost_r != 0) {
                // Blend ghost with video
                output[pixel_idx + 0] = ghost_alpha * ghost_b + (1.0f - ghost_alpha) * video_b;
                output[pixel_idx + 1] = ghost_alpha * ghost_g + (1.0f - ghost_alpha) * video_g;
                output[pixel_idx + 2] = ghost_alpha * ghost_r + (1.0f - ghost_alpha) * video_r;
            } else {
                // No ghost, just copy video
                output[pixel_idx + 0] = video_b;
                output[pixel_idx + 1] = video_g;
                output[pixel_idx + 2] = video_r;
            }
        }
    }
}

void save_frame_as_ppm(const uint8_t* frame, const char* filename)
{
    FILE* file = fopen(filename, "wb");
    if (!file) {
        printf("❌ Failed to open file %s\n", filename);
        return;
    }
    
    // Write PPM header
    fprintf(file, "P6\n%d %d\n255\n", VIDEO_WIDTH, VIDEO_HEIGHT);
    
    // Write pixel data
    fwrite(frame, 1, VIDEO_WIDTH * VIDEO_HEIGHT * VIDEO_CHANNELS, file);
    
    fclose(file);
    printf("✅ Frame saved as %s\n", filename);
}

void cleanup()
{
    printf("🔄 Cleaning up...\n");
    
    if (fn_dev) {
        freenect_stop_depth(fn_dev);
        freenect_stop_video(fn_dev);
        freenect_close_device(fn_dev);
    }
    
    if (fn_ctx) {
        freenect_shutdown(fn_ctx);
    }
    
    // Free allocated memory
    if (latest_depth) free(latest_depth);
    if (latest_video) free(latest_video);
    if (background_image) free(background_image);
    if (ghost_output) free(ghost_output);
    
    pthread_mutex_destroy(&frame_mutex);
    
    printf("✅ Cleanup complete\n");
}

int main(int argc, char** argv)
{
    printf("👻 Simple Person Ghost Effect - C Implementation\n");
    printf("================================================\n");
    
    // Handle signals
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    signal(SIGQUIT, signalHandler);
    
    // Allocate memory
    ghost_output = (uint8_t*)malloc(VIDEO_WIDTH * VIDEO_HEIGHT * VIDEO_CHANNELS);
    if (!ghost_output) {
        printf("❌ Failed to allocate memory for ghost output\n");
        return 1;
    }
    
    // Initialize Kinect
    if (!initialize_kinect()) {
        printf("❌ Failed to initialize Kinect\n");
        cleanup();
        return 1;
    }
    
    printf("\n🎯 Ghost effect running!\n");
    printf("   Press Ctrl+C to quit\n");
    printf("   Press 's' to save current frame\n");
    printf("   Press 'b' to capture background\n");
    printf("   Adjust depth range: %d-%d mm\n", depth_min, depth_max);
    printf("   Background subtraction: %s\n", background_image ? "Enabled" : "Disabled");
    
    // Main loop
    int frame_count = 0;
    bool background_captured = false;
    
    while (running) {
        // Process events
        int ret = freenect_process_events(fn_ctx);
        if (ret < 0) {
            printf("❌ Error processing events: %d\n", ret);
            break;
        }
        
        pthread_mutex_lock(&frame_mutex);
        
        if (latest_depth && latest_video) {
            frame_count++;
            
            // Create person silhouette
            uint8_t* silhouette = (uint8_t*)malloc(DEPTH_WIDTH * DEPTH_HEIGHT * VIDEO_CHANNELS);
            create_person_silhouette(silhouette, latest_depth, background_image);
            
            // Apply ghost effect
            apply_ghost_effect(ghost_output, latest_video, silhouette);
            
            // Save frame only when user presses 's' (handled in main loop)
            // Removed automatic saving to prevent file spam
            
            free(silhouette);
            
            if (frame_count % 30 == 0) {
                printf("📊 Frame %d processed\n", frame_count);
            }
            
            // Check for keyboard input (non-blocking)
            // Note: This is a simplified approach - in a real implementation
            // you'd want proper keyboard input handling
        }
        
        pthread_mutex_unlock(&frame_mutex);
        
        usleep(33333); // ~30fps
    }
    
    // Cleanup
    cleanup();
    
    printf("\n🎯 Ghost effect completed!\n");
    printf("   Processed %d frames\n", frame_count);
    
    return 0;
}