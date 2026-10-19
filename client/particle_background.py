# client/particle_background.py
"""
Animated particle background representing quantum bits
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, QPointF, Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
import random
import math


class Particle:
    """Single particle representing a qubit"""
    
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = random.uniform(1.5, 3.5)
        self.alpha = random.randint(80, 180)
        
    def update(self, width, height):
        """Update particle position"""
        self.x += self.vx
        self.y += self.vy
        
        # Wrap around edges
        if self.x < 0:
            self.x = width
        elif self.x > width:
            self.x = 0
            
        if self.y < 0:
            self.y = height
        elif self.y > height:
            self.y = 0


class ParticleBackground(QWidget):
    """Animated particle background widget"""
    
    def __init__(self, parent=None, num_particles=50):
        super().__init__(parent)
        self.particles = []
        self.num_particles = num_particles
        self.connection_distance = 120
        self.active = True
        
        # Set transparent background
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        
        # Initialize particles
        self._init_particles()
        
        # Setup animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_particles)
        self.timer.start(30)  # ~33 FPS
        
    def _init_particles(self):
        """Initialize particle positions"""
        w, h = self.width(), self.height()
        if w == 0 or h == 0:
            w, h = 800, 600
            
        for _ in range(self.num_particles):
            x = random.uniform(0, w)
            y = random.uniform(0, h)
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.3, 0.8)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x, y, vx, vy))
    
    def _update_particles(self):
        """Update all particles and trigger repaint"""
        if not self.active:
            return
            
        w, h = self.width(), self.height()
        for particle in self.particles:
            particle.update(w, h)
        self.update()
    
    def paintEvent(self, event):
        """Draw particles and connections"""
        if not self.active:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw connections between nearby particles
        for i, p1 in enumerate(self.particles):
            for p2 in self.particles[i+1:]:
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist < self.connection_distance:
                    # Fade based on distance
                    alpha = int((1 - dist / self.connection_distance) * 40)
                    pen = QPen(QColor(0, 229, 255, alpha), 1)
                    painter.setPen(pen)
                    painter.drawLine(
                        int(p1.x), int(p1.y),
                        int(p2.x), int(p2.y)
                    )
        
        # Draw particles
        for particle in self.particles:
            # Gradient color based on position
            color = QColor(0, 229, 255, particle.alpha)  # Cyan #00e5ff
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                QPointF(particle.x, particle.y),
                particle.size, particle.size
            )
    
    def setActive(self, active):
        """Enable/disable animation"""
        self.active = active
        if active:
            self.timer.start()
        else:
            self.timer.stop()
        self.update()
    
    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        # Reinitialize particles on resize
        if len(self.particles) == 0:
            self._init_particles()
