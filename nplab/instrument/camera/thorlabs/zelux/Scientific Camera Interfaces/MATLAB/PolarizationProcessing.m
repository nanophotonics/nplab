% Matlab sample for using TSICamera and polarization processing DotNET 
% interface with polarization camera. 

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
    
    % Check if the camera is Polarization camera.
    cameraSensorType = tlCamera.CameraSensorType;
    isPolarizationCamera = cameraSensorType == Thorlabs.TSI.TLCameraInterfaces.CameraSensorType.MonochromePolarized;
    if (isPolarizationCamera)
        % Load polarization processing .NET assemblies
        NET.addAssembly([pwd, '\Thorlabs.TSI.PolarizationProcessor.dll']);
        
        % Create polarization processor SDK.
        polarizationProcessorSDK = Thorlabs.TSI.PolarizationProcessor.PolarizationProcessorSDK;
        
        % Create polarization processor
        polarizationProcessor = polarizationProcessorSDK.CreatePolarizationProcessor;

        % Query the polar phase of the camera.
        polarPhase = tlCamera.PolarPhase;
    end
    
    % Set exposure time and gain of the camera.
    tlCamera.ExposureTime_us = 20000;
    
    figure(1)
    
    % Check if the camera supports setting "Gain"
    gainRange = tlCamera.GainRange;
    if (gainRange.Maximum > 0)
        tlCamera.Gain = 0;
    end
    
    % Set the FIFO frame buffer size. Default size is 1.
    tlCamera.MaximumNumberOfFramesToQueue = 5;
    
    % Start continuous image acquisition
    disp('Starting continuous image acquisition.');
    tlCamera.OperationMode = Thorlabs.TSI.TLCameraInterfaces.OperationMode.SoftwareTriggered;
    tlCamera.FramesPerTrigger_zeroForUnlimited = 0;
    tlCamera.Arm;
    tlCamera.IssueSoftwareTrigger;
    
    maxPixelValue = double(2^tlCamera.BitDepth - 1);

    numberOfFramesToAcquire = 10;
    frameCount = 0;
    while frameCount < numberOfFramesToAcquire
        % Check if image buffer has been filled
        if (tlCamera.NumberOfQueuedFrames > 0)
            
            % If data processing in Matlab falls behind camera image
            % acquisition, the FIFO image frame buffer could be filled up,
            % which would result in missed frames.
            if (tlCamera.NumberOfQueuedFrames > 1)
                disp(['Data processing falling behind acquisition. ' num2str(tlCamera.NumberOfQueuedFrames) ' remains']);
            end
            
            % Get the pending image frame.
            imageFrame = tlCamera.GetPendingFrameOrNull;
            if ~isempty(imageFrame)
                frameCount = frameCount + 1;
                % For color images, the image data is in BGR format.
                imageData = imageFrame.ImageData.ImageData_monoOrBGR;
                
                disp(['Image frame number: ' num2str(imageFrame.FrameNumber)]);
                
                % TODO: custom image processing code goes here
                imageHeight = imageFrame.ImageData.Height_pixels;
                imageWidth = imageFrame.ImageData.Width_pixels;
                bitDepth = imageFrame.ImageData.BitDepth;
                maxOutput = uint16(2^bitDepth - 1);
                if (isPolarizationCamera)
                    % Allocate memory for processed Azimuth image output.
                    outputoAzimuthData = NET.createArray('System.UInt16',imageHeight * imageWidth);
                    % Calculate the Azimuth image.
                    polarizationProcessor.TransformToAzimuth(polarPhase, imageData, int32(0), int32(0), imageWidth, imageHeight, ...
                        bitDepth, maxOutput, outputoAzimuthData);
                                        
                    % Convert the angle data to degrees (-90 to 90 degrees)
                    imageAngleData = double(outputoAzimuthData) / double(maxOutput) * 180 - 90;
                    % Display the Azimuth image
                    imageAngle2D = reshape(imageAngleData, [imageWidth, imageHeight]);
                    figure(1)
                    set(gcf, 'Position', [100 300 550 400]);                    
                    imagesc(imageAngle2D'), colormap(jet), colorbar, axis equal
                    title('Azimuth image (-90 degrees to 90 degrees)')
                    
                    % Allocate memory for processed Degree of Linear Polarization (DoLP) image output.
                    outputoDoLPData = NET.createArray('System.UInt16',imageHeight * imageWidth);
                    % Calculate the Degree of Linear Polarization (DoLP) image.
                    polarizationProcessor.TransformToDoLP(polarPhase, imageData, int32(0), int32(0), imageWidth, imageHeight, ...
                        bitDepth, maxOutput, outputoDoLPData);
                                        
                    % Convert the DoLP data to percent (0 to 100)
                    imageDoLPData = double(outputoDoLPData) / double(maxOutput) * 100;
                    % Display the DoLP image
                    imageDoLP2D = reshape(imageDoLPData, [imageWidth, imageHeight]);
                    figure(2)
                    set(gcf, 'Position', [700 300 550 400]);                    
                    imagesc(imageDoLP2D'), colormap(jet), colorbar, axis equal
                    title('Degree of Linear Polarization image (0 to 100 percent)')
                    
                    % Allocate memory for processed Intensity image output.
                    outputIntensityData = NET.createArray('System.UInt16',imageHeight * imageWidth);
                    % Calculate the Intensity image.
                    polarizationProcessor.TransformToIntensity(polarPhase, imageData, int32(0), int32(0), imageWidth, imageHeight, ...
                        bitDepth, maxOutput, outputIntensityData);
                                        
                    % Display the Intensity image
                    imageIntensity2D = reshape(uint16(outputIntensityData), [imageWidth, imageHeight]);
                    figure(3)
                    set(gcf, 'Position', [1300 300 550 400]);                    
                    imagesc(imageIntensity2D'), colormap(hot), colorbar, axis equal  
                    title('Intensity image')

                else
                    imageData2D = reshape(uint16(imageData), [imageWidth, imageHeight]);
                    figure(1),imagesc(imageData2D'), colormap(gray), colorbar
                end
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
    
    if (isPolarizationCamera)
        polarizationProcessor.Dispose;
        delete(polarizationProcessor);
        polarizationProcessorSDK.Dispose;
        delete(polarizationProcessorSDK);
    end
end

% Release the serial numbers
delete(serialNumbers);

% Release the TLCameraSDK.
tlCameraSDK.Dispose;
delete(tlCameraSDK);
