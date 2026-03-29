class A:# =========================================================
            # KARAKAMSHA HIGHLIGHT (Fully Cached Glow & Fast Stardust)
            # =========================================================
            is_d1_chart = self.title and (self.title == "D1" or self.title.startswith("D1 "))
            
            if getattr(self, "show_karakamsha", True) and is_d1_chart and getattr(self, "chart_data", None) and not getattr(self, "use_circular", False):
                ak_planet = next((p for p in self.chart_data.get("planets", []) if p.get("is_ak")), None)
                
                if ak_planet and "deg_in_sign" in ak_planet and "sign_index" in ak_planet:
                    ak_d9_sign = int(ak_planet["sign_index"] * 9 + ak_planet["deg_in_sign"] / (30.0 / 9.0)) % 12
                    asc_idx = self.rotated_asc_sign_idx if getattr(self, 'rotated_asc_sign_idx', None) is not None else self.chart_data["ascendant"]["sign_index"]
                    k_house = ((ak_d9_sign - asc_idx) % 12) + 1
                    
                    # --- 2. ALIGNMENT OFFSET FIX ---
                    # Use target_layout instead of current_layout so the internal coordinates
                    # instantly match the snapping poly border, preventing drift!
                    h_data = self.target_layout["houses"].get(k_house)
                    
                    if h_data and k_house in self.house_polys:
                        poly = self.house_polys[k_house]
                        
                        house_tints = [t["color"] for t in self.target_layout.get("tints", []) if t["h2"] == k_house]
                        if not house_tints:
                            glow_color = QColor(255, 215, 0) 
                        else:
                            bg_r, bg_g, bg_b = 255.0, 255.0, 255.0 
                            for tc in house_tints:
                                alpha = tc.alphaF()
                                bg_r = (tc.red() * alpha) + (bg_r * (1.0 - alpha))
                                bg_g = (tc.green() * alpha) + (bg_g * (1.0 - alpha))
                                bg_b = (tc.blue() * alpha) + (bg_b * (1.0 - alpha))
                            
                            bg_color = QColor(int(bg_r), int(bg_g), int(bg_b))
                            bg_h, bg_s, _, _ = bg_color.getHsv()
                            
                            comp_h = 180 if (bg_h == -1 or bg_s < 15) else (bg_h + 180) % 360
                            glow_color = QColor.fromHsv(comp_h, 120, 255) 
                            
                        particle_color = QColor(255, 255, 255)
                        
                        # --- 3. EXTREME CACHING ---
                        # x and y are now included to safely invalidate if the layout moves 
                        cache_key = (k_house, self.width(), self.height(), x, y, w, h, glow_color.rgb(), getattr(self, "outline_mode", ""), dpr)
                        if getattr(self, '_k_cache_key', None) != cache_key:
                            self._k_cache_key = cache_key
                            
                            self._k_seeds = [(abs(math.sin(i * 37.1)), abs(math.cos(i * 91.3))) for i in range(24)]
                            
                            self._k_glow_pix = QPixmap(pixel_w, pixel_h)
                            self._k_glow_pix.setDevicePixelRatio(dpr)
                            self._k_glow_pix.fill(Qt.GlobalColor.transparent)
                            
                            p_cache = QPainter(self._k_glow_pix)
                            p_cache.setRenderHint(QPainter.RenderHint.Antialiasing)
                            
                            # Bake the heavy Aura directly into the cache
                            p_cache.save()
                            clip_path = QPainterPath()
                            clip_path.addPolygon(poly)
                            p_cache.setClipPath(clip_path)
                            
                            radial_grad = QRadialGradient(QPointF(h_data["x"], h_data["y"]), w * 0.18)
                            radial_grad.setColorAt(0.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 180))
                            radial_grad.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
                            p_cache.setPen(Qt.PenStyle.NoPen)
                            p_cache.setBrush(QBrush(radial_grad))
                            p_cache.drawPolygon(poly)
                            p_cache.restore()
                            
                            # Bake the heavy Edge Bloom
                            def get_inset_poly(offset):
                                pts = []
                                for pt in poly:
                                    dx = h_data["x"] - pt.x()
                                    dy = h_data["y"] - pt.y()
                                    dist = max(1, math.hypot(dx, dy))
                                    pts.append(QPointF(pt.x() + (dx / dist) * offset, pt.y() + (dy / dist) * offset))
                                return QPolygonF(pts)

                            dynamic_inset = (max(1.0, w * 0.005) / 2.0)
                            if self.outline_mode == "Regime (Forces)" and h_data.get("regime_colors", []):
                                dynamic_inset += 4.25 + ((len(h_data["regime_colors"]) - 1) * 3.5) + 3.0
                            elif self.outline_mode != "Regime (Forces)" and h_data.get("outline_width", 1.0) > 1.05:
                                dynamic_inset += 4.25 + 3.0
                            else:
                                dynamic_inset += 5.0

                            inset_poly = get_inset_poly(dynamic_inset)
                            p_cache.setBrush(Qt.BrushStyle.NoBrush)
                            
                            glow_widths = [15.0, 10.0, 5.0, 2.0] 
                            for width_mult in glow_widths:
                                blur_thickness = max(width_mult, w * (width_mult / 1000.0))
                                p_cache.setPen(QPen(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 100), blur_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                                p_cache.drawPolygon(inset_poly)
                                
                            p_cache.setPen(QPen(QColor(255, 255, 255, 255), max(1.5, w * 0.0025), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
                            p_cache.drawPolygon(inset_poly)
                            p_cache.end()
                            
                        # --- LIGHTNING FAST ANIMATION LOOP ---
                        current_time = time.time()
                        breath = (math.sin(current_time * 2.0) + 1.0) / 2.0
                        
                        # 1. Instantly stamp the baked glow image (Pulsing opacity naturally)
                        painter.save()
                        pulse_opacity = 0.5 + (breath * 0.5) 
                        painter.setOpacity(pulse_opacity)
                        painter.drawPixmap(0, 0, self._k_glow_pix)
                        painter.restore()
                        
                        # 2. Draw purely dynamic Stardust
                        painter.save()
                        clip_path = QPainterPath()
                        clip_path.addPolygon(poly)
                        painter.setClipPath(clip_path)
                        
                        rect = poly.boundingRect()
                        painter.setPen(Qt.PenStyle.NoPen)
                        
                        for i in range(24):
                            seed1, seed2 = self._k_seeds[i]
                            
                            speed = 14 + (seed1 * 20)      
                            phase = i * 45.2               
                            sway_freq = 0.8 + seed2 * 1.5  
                            
                            y_offset = ((current_time * speed) + phase) % rect.height()
                            y = rect.bottom() - y_offset
                            sway = math.sin(current_time * sway_freq + i) * (w * 0.012)
                            x = rect.left() + (seed1 * rect.width()) + sway
                            
                            twinkle = (math.sin(current_time * 4 + i) + 1) / 2.0
                            p_opacity = int(130 + (twinkle * 125))
                            p_size = max(2.0, w * 0.0035) + (seed2 * w * 0.0035)
                            
                            painter.setBrush(QColor(particle_color.red(), particle_color.green(), particle_color.blue(), p_opacity))
                            painter.drawEllipse(QPointF(x, y), p_size, p_size)

                        painter.restore() 
            # =========================================================


