import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export default function CncLathe3DCanvas({
  isSimulating = false,
  condition = 'Normal',
  rotationalSpeed = 1500,
  toolWear = 0,
}) {
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const width = container.clientWidth || 400
    const height = container.clientHeight || 260

    // Scene & Camera setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a1c27)

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    camera.position.set(4, 3, 5.5)
    camera.lookAt(0, 0, 0)

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    container.appendChild(renderer.domElement)

    // Lighting setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7)
    scene.add(ambientLight)

    const dirLight = new THREE.DirectionalLight(0x38bdf8, 1.2)
    dirLight.position.set(5, 8, 4)
    dirLight.castShadow = true
    scene.add(dirLight)

    const spotLight = new THREE.SpotLight(0xffffff, 1.5)
    spotLight.position.set(-4, 6, 3)
    scene.add(spotLight)

    // Status Glow Color setup based on Condition
    let statusHex = 0x10b981 // Normal emerald
    if (condition === 'Warning') statusHex = 0xf59e0b // Amber
    if (condition === 'Critical') statusHex = 0xef4444 // Red

    // Status LED light
    const statusPointLight = new THREE.PointLight(statusHex, 2, 8)
    statusPointLight.position.set(0, 1.5, 0)
    scene.add(statusPointLight)

    // CNC Lathe Group Assembly
    const latheGroup = new THREE.Group()

    // 1. Heavy Machine Bed / Base
    const bedGeo = new THREE.BoxGeometry(4.2, 0.4, 2.2)
    const bedMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.5,
      metalness: 0.8,
    })
    const bedMesh = new THREE.Mesh(bedGeo, bedMat)
    bedMesh.position.set(0, -0.6, 0)
    latheGroup.add(bedMesh)

    // Bed Rails / Linear Guides
    const railMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 })
    const rail1 = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.08, 0.12), railMat)
    rail1.position.set(0, -0.36, -0.4)
    const rail2 = rail1.clone()
    rail2.position.set(0, -0.36, 0.4)
    latheGroup.add(rail1)
    latheGroup.add(rail2)

    // 2. Headstock (Main Drive Housing left side)
    const headstockGeo = new THREE.BoxGeometry(1.2, 1.6, 1.8)
    const headstockMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.4,
      metalness: 0.7,
    })
    const headstockMesh = new THREE.Mesh(headstockGeo, headstockMat)
    headstockMesh.position.set(-1.4, 0.4, 0)
    latheGroup.add(headstockMesh)

    // Status Indicator Light Pillar on Headstock
    const indicatorGeo = new THREE.CylinderGeometry(0.1, 0.1, 0.3, 16)
    const indicatorMat = new THREE.MeshStandardMaterial({
      color: statusHex,
      emissive: statusHex,
      emissiveIntensity: 0.8,
      roughness: 0.2,
    })
    const indicatorMesh = new THREE.Mesh(indicatorGeo, indicatorMat)
    indicatorMesh.position.set(-1.4, 1.35, -0.6)
    latheGroup.add(indicatorMesh)

    // 3. Rotating Spindle Chuck (Attaches workpiece)
    const chuckGroup = new THREE.Group()
    chuckGroup.position.set(-0.7, 0.4, 0)

    const chuckBodyGeo = new THREE.CylinderGeometry(0.55, 0.55, 0.4, 32)
    const chuckMat = new THREE.MeshStandardMaterial({
      color: 0x475569,
      metalness: 0.95,
      roughness: 0.25,
    })
    const chuckBody = new THREE.Mesh(chuckBodyGeo, chuckMat)
    chuckBody.rotation.z = Math.PI / 2
    chuckGroup.add(chuckBody)

    // 3 Stepped Chuck Jaws
    const jawGeo = new THREE.BoxGeometry(0.18, 0.3, 0.15)
    const jawMat = new THREE.MeshStandardMaterial({ color: 0xc0c6d4, metalness: 0.9, roughness: 0.1 })
    for (let i = 0; i < 3; i++) {
      const jaw = new THREE.Mesh(jawGeo, jawMat)
      const angle = (i * Math.PI * 2) / 3
      jaw.position.set(0, Math.cos(angle) * 0.38, Math.sin(angle) * 0.38)
      chuckGroup.add(jaw)
    }
    latheGroup.add(chuckGroup)

    // 4. Workpiece Cylindrical Stock
    const workpieceGroup = new THREE.Group()
    workpieceGroup.position.set(-0.5, 0.4, 0)

    const wpGeo = new THREE.CylinderGeometry(0.3, 0.3, 1.8, 32)
    const wpMat = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0,
      metalness: 0.85,
      roughness: 0.3,
    })
    const workpieceMesh = new THREE.Mesh(wpGeo, wpMat)
    workpieceMesh.rotation.z = Math.PI / 2
    workpieceMesh.position.set(0.9, 0, 0)
    workpieceGroup.add(workpieceMesh)

    latheGroup.add(workpieceGroup)

    // 5. Tool Post & Carriages (Right Side Tool Holder)
    const toolPostGroup = new THREE.Group()
    toolPostGroup.position.set(0.4, 0.1, 0.45)

    const carriageGeo = new THREE.BoxGeometry(0.8, 0.3, 0.9)
    const carriageMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7, roughness: 0.4 })
    const carriageMesh = new THREE.Mesh(carriageGeo, carriageMat)
    toolPostGroup.add(carriageMesh)

    const turretGeo = new THREE.BoxGeometry(0.45, 0.5, 0.45)
    const turretMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.3 })
    const turretMesh = new THREE.Mesh(turretGeo, turretMat)
    turretMesh.position.set(0, 0.35, 0)
    toolPostGroup.add(turretMesh)

    // Cutting Insert Bit pointing at workpiece
    const insertGeo = new THREE.ConeGeometry(0.08, 0.25, 4)
    const insertMat = new THREE.MeshStandardMaterial({
      color: condition === 'Critical' ? 0xef4444 : 0xf59e0b,
      metalness: 0.9,
      roughness: 0.1,
    })
    const insertMesh = new THREE.Mesh(insertGeo, insertMat)
    insertMesh.rotation.z = -Math.PI / 2
    insertMesh.position.set(0.2, 0.35, -0.25)
    toolPostGroup.add(insertMesh)

    latheGroup.add(toolPostGroup)

    // 6. Tailstock (Right side support)
    const tailstockGeo = new THREE.BoxGeometry(0.8, 1.0, 1.2)
    const tailstockMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.7, roughness: 0.5 })
    const tailstockMesh = new THREE.Mesh(tailstockGeo, tailstockMat)
    tailstockMesh.position.set(1.5, 0.1, 0)
    latheGroup.add(tailstockMesh)

    scene.add(latheGroup)

    // Animation Loop
    let animationFrameId
    let rotationAngle = 0

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)

      if (isSimulating) {
        // Rotate chuck and workpiece scaled by rotational speed
        const speedFactor = (rotationalSpeed / 1500) * 0.08
        rotationAngle += speedFactor
        chuckGroup.rotation.x = rotationAngle
        workpieceGroup.rotation.x = rotationAngle

        // Subtle tool vibration & wear offset
        const wearOffset = Math.sin(Date.now() * 0.005) * 0.015
        toolPostGroup.position.z = 0.45 + (toolWear / 220) * 0.05 + wearOffset
      }

      // Gentle lathe group floating rotation for perspective viewing
      latheGroup.rotation.y = Math.sin(Date.now() * 0.0005) * 0.12

      renderer.render(scene, camera)
    }

    animate()

    // Handle Window Resize
    const handleResize = () => {
      if (!containerRef.current) return
      const w = containerRef.current.clientWidth || 400
      const h = containerRef.current.clientHeight || 260
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }

    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', handleResize)
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
      renderer.dispose()
    }
  }, [isSimulating, condition, rotationalSpeed, toolWear])

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '240px',
        borderRadius: '8px',
        overflow: 'hidden',
        position: 'relative',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        background: '#0a1c27',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: '10px',
          left: '12px',
          fontSize: '0.72rem',
          fontWeight: 700,
          letterSpacing: '0.05em',
          color: '#94a3b8',
          textTransform: 'uppercase',
          pointerEvents: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}
      >
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isSimulating ? '#10b981' : '#64748b',
            boxShadow: isSimulating ? '0 0 8px #10b981' : 'none',
          }}
        />
        CNC Twin Visualization · {isSimulating ? 'Active' : 'Standby'}
      </div>
    </div>
  )
}
