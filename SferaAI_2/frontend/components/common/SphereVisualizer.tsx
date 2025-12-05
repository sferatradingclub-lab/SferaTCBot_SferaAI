import React, { useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useVoiceAssistant } from '@livekit/components-react';
import { RemoteAudioTrack } from 'livekit-client';

interface SphereVisualizerProps {
    isActive: boolean;
}

const BAR_COUNT = 128; // Number of bars in the circle
const RADIUS = 2.5; // Restored Radius to original size

const Bar: React.FC<{ index: number; dataArray: Uint8Array | null }> = ({ index, dataArray }) => {
    const meshRef = useRef<THREE.Mesh>(null);

    // Pre-calculate static properties
    const { rotation, color, angle } = useMemo(() => {
        // Rotate by +PI/2 so Index 0 (Bass) is at the Top (12 o'clock)
        const angle = (index / BAR_COUNT) * Math.PI * 2 + Math.PI / 2;
        const normalizedY = (Math.sin(angle + Math.PI / 2) + 1) / 2; // 0 to 1 (Bottom to Top)

        // Gradient: Cyan (Top) -> Purple (Bottom)
        const hue = 0.75 - (normalizedY * 0.25);

        // Use string HSL for React Three Fiber
        // Lightness 0.5 for maximum color saturation
        const color = `hsl(${hue * 360}, 100%, 50%)`;

        return {
            rotation: new THREE.Euler(0, 0, angle - Math.PI / 2),
            color,
            angle
        };
    }, [index]);

    useFrame(() => {
        if (!meshRef.current || !dataArray) return;

        // Mirrored Spectrum Logic with Logarithmic Mapping
        const halfCount = BAR_COUNT / 2;
        let relativeIndex = index;
        if (index > halfCount) {
            relativeIndex = BAR_COUNT - index;
        }

        // Logarithmic mapping to spread bass frequencies across more bars
        const normalizedIndex = relativeIndex / halfCount; // 0 to 1
        // Power of 2.5 spreads the bass out more
        const logIndex = Math.pow(normalizedIndex, 2.5);
        const binIndex = Math.floor(logIndex * 64); // Map to first 64 bins (most active range)

        // Safety check
        const safeBinIndex = Math.min(Math.max(binIndex, 0), dataArray.length - 1);

        const dataValue = dataArray[safeBinIndex] || 0;

        // Scale: 0 if silent (threshold 5), otherwise scale up significantly
        // Added small base 0.1 for active sound and increased multiplier to 1.5
        const scaleY = dataValue > 5 ? 0.1 + (dataValue / 255) * 1.5 : 0;

        meshRef.current.scale.set(1, scaleY, 1);
        meshRef.current.visible = scaleY > 0.001; // Hide completely if scale is near 0

        // ANCHOR LOGIC
        const currentRadius = RADIUS + (0.25 * scaleY);
        const x = Math.cos(angle) * currentRadius;
        const y = Math.sin(angle) * currentRadius;

        meshRef.current.position.set(x, y, 0);
    });

    return (
        <mesh ref={meshRef} rotation={rotation}>
            <planeGeometry args={[0.06, 0.5]} />
            <meshBasicMaterial color={color} toneMapped={false} />
        </mesh>
    );
};

const SpectrumScene: React.FC<{ analyser: AnalyserNode | null, dataArray: Uint8Array | null, isActive: boolean }> = ({ analyser, dataArray, isActive }) => {
    useFrame(() => {
        if (!analyser || !dataArray) return;

        if (isActive) {
            // TS Error workaround
            analyser.getByteFrequencyData(dataArray as unknown as Uint8Array);
        } else {
            dataArray.fill(0);
        }
    });

    return (
        <group>
            {Array.from({ length: BAR_COUNT }).map((_, i) => (
                <Bar key={i} index={i} dataArray={dataArray} />
            ))}
        </group>
    );
};

export const SphereVisualizer: React.FC<SphereVisualizerProps> = ({ isActive }) => {
    const { audioTrack } = useVoiceAssistant();
    const analyserRef = useRef<AnalyserNode | null>(null);
    const dataArrayRef = useRef<Uint8Array | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

    useEffect(() => {
        if (!audioTrack || !audioTrack.publication?.track) return;

        const track = audioTrack.publication.track as unknown as RemoteAudioTrack;
        const mediaStreamTrack = track.mediaStreamTrack;

        if (!mediaStreamTrack) return;

        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = ctx;

        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;
        analyserRef.current = analyser;

        const source = ctx.createMediaStreamSource(new MediaStream([mediaStreamTrack]));
        sourceRef.current = source;
        source.connect(analyser);

        dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);

        return () => {
            source.disconnect();
            analyser.disconnect();
            ctx.close();
        };
    }, [audioTrack]);

    return (
        <div className={`relative w-[200px] h-[200px] sm:w-[250px] sm:h-[250px] md:w-[300px] md:h-[300px] transition-opacity duration-500 ${isActive ? 'opacity-100' : 'opacity-50'}`} style={{ background: 'transparent' }}>
            {/* Moved camera back to z=8 to prevent clipping */}
            <Canvas camera={{ position: [0, 0, 8], fov: 50 }} gl={{ alpha: true, antialias: true }} style={{ background: 'transparent' }}>
                <SpectrumScene analyser={analyserRef.current} dataArray={dataArrayRef.current} isActive={isActive} />
            </Canvas>
        </div>
    );
};
