% Simple Matlab sample for using TSICamera DotNET interface with polling-
% based image acquisition. If the camera is color, returns Bayer-patterned
% mono color images.

clear
close all

% Load TLCamera DotNet assembly. The assembly .dll is assumed to be in the 
% same folder as the scripts.
NET.addAssembly([pwd, '\Thorlabs.TSI.TLCamera.dll']);
disp('Dot NET assembly loaded.');

tlCameraSDK = Thorlabs.TSI.TLCamera.TLCameraSDK.OpenTLCameraSDK;

% Get serial numbers of connected TLCameras.
serialNumbers = tlCameraSDK.DiscoverAvailableCameras;
disp([num2str(serialNumbers.Count), ' camera was discovered.']);

if (serialNumbers.Count > 0)
    % Open the first TLCamera using the serial number.
    disp('Opening the first camera')
    tlCamera = tlCameraSDK.OpenCamera(serialNumbers.Item(0), false);
    
    % Set exposure time and gain of the camera.
    tlCamera.ExposureTime_us = 200000;
    
    % Check if the camera supports setting "Gain"
    gainRange = tlCamera.GainRange;
    if (gainRange.Maximum > 0)
        tlCamera.Gain = 0;
    end
    
    % Set the FIFO frame buffer size. Default size is 1.
    tlCamera.MaximumNumberOfFramesToQueue = 5;
    
    figure(1)
    
    % Start continuous image acquisition
    disp('Starting continuous image acquisition.');
    tlCamera.OperationMode = Thorlabs.TSI.TLCameraInterfaces.OperationMode.SoftwareTriggered;
    tlCamera.FramesPerTrigger_zeroForUnlimited = 0;
    tlCamera.Arm;
    tlCamera.IssueSoftwareTrigger;
    maxPixelIntensity = double(2^tlCamera.BitDepth - 1);

    numberOfFramesToAcquire = 10;
    frameCount = 0;
    while frameCount < numberOfFramesToAcquire
        % Check if image buffer has been filled
        if (tlCamera.NumberOfQueuedFrames > 0)
            
            % If data processing in Matlab falls behind camera image
            % acquisition, the FIFO image frame buffer could overflow,
            % which would result in missed frames.
            if (tlCamera.NumberOfQueuedFrames > 1)
                disp(['Data processing falling behind acquisition. ' num2str(tlCamera.NumberOfQueuedFrames) ' remains']);
            end
            
            % Get the pending image frame.
            imageFrame = tlCamera.GetPendingFrameOrNull;
            if ~isempty(imageFrame)
                frameCount = frameCount + 1;
                
                % Get the image data as 1D uint16 array
                imageData = uint16(imageFrame.ImageData.ImageData_monoOrBGR);

                disp(['Image frame number: ' num2str(imageFrame.FrameNumber)]);

                % TODO: custom image processing code goes here
                imageHeight = imageFrame.ImageData.Height_pixels;
                imageWidth = imageFrame.ImageData.Width_pixels;
                imageData2D = reshape(imageData, [imageWidth, imageHeight]);
                figure(1),imagesc(imageData2D'), colormap(gray), colorbar
            end
            
            % Release the image frame
            delete(imageFrame);
        end
        drawnow;
    end
    
    % Stop continuous image acquisition
    disp('Stopping continuous image acquisition.');
    tlCamera.Disarm;
    
    % Release the TLCamera
    disp('Releasing the camera');
    tlCamera.Dispose;
    delete(tlCamera);
end

% Release the serial numbers
delete(serialNumbers);

% Release the TLCameraSDK.
tlCameraSDK.Dispose;
delete(tlCameraSDK);
