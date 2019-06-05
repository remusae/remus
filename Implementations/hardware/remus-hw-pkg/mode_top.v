`include "params.vh"
module mode_top (
		 output [BUSWIDTH-1:0] 	  pdo,
		 output [5:0] 		  constant,

		 input [BUSWIDTH-1:0] 	  pdi,
		 input [BUSWIDTH-1:0] 	  sdi,
		 input [7:0] 		  dold, dnew,
		 input [BUSWIDTHBYTE-1:0] decrypt,
		 input 			  clk,
		 input 			  srst, senc, sse,
		 input 			  xrst, xenc, xse,
		 input 			  erst,
		 input 			  sl,
`ifdef TWO
		 input 			  vse, venc, vf, vl, ll, kdf, fv,
 `ifdef MR
		 input vs2,
 `endif
`endif		 
		 input 			  correct_cnt
   ) ;
   parameter BUSWIDTH = 32;
   parameter BUSWIDTHBYTE = 4;
   parameter FFTYPE = 1;   
      
   wire [127:0]  tk1;
   wire [127:0]  tka;
   wire [127:0]  tkc;   
   wire [127:0]  skinnyS;
   wire [127:0]  skinnyX;
   wire [127:0]  S, TKX;
   wire [BUSWIDTH-1:0] li;
`ifdef TWO
   wire [BUSWIDTH-1:0] vo;
   wire [127:0]        K;  
`endif

   assign tkc = correct_cnt ? TKX : tka;
`ifdef TWO
   assign li = ll ? vo : (sl ? pdo : sdi);   
`else
   assign li = sl ? pdo : sdi;   
`endif

`ifdef TWO
   assign K = tka ^ {128'h01};
`endif
   
   generate if (BUSWIDTH == 32) begin
      state_update_32b #(.FFTYPE(FFTYPE)) 
      STATE (.state(S), .pdo(pdo), .skinny_state(skinnyS), .pdi(pdi),
`ifdef TWO	     
	     .vl(vl), .vf(vf), .vse(vse), .venc(venc), .vo(vo), .kdf(kdf), .fv(fv),
 `ifdef MR
	     .vs2(vs2), .sdi(sdi),
 `endif
`endif	     
	     .clk(clk), .rst(srst), .enc(senc), .se(sse),
	     .decrypt(decrypt));
`ifdef TWO
      tkx_update_32b TKEYX (.tkx(TKX), .skinny_tkx(skinnyX), .skinny_tkx_revert(tk1), 
			    .sdi(li), .clk(clk), .rst(xrst), .enc(xenc), .se(xse), .L(K), .kdf(kdf));
`else
      tkx_update_32b TKEYX (.tkx(TKX), .skinny_tkx(skinnyX), .skinny_tkx_revert(tk1), 
			    .sdi(li), .clk(clk), .rst(xrst), .enc(xenc), .se(xse));
`endif
   end
   endgenerate
   
   pt8 permA (.tk1o(tka), .tk1i(TKX));
   doubling CNT (.so(tk1), .si(tkc), .dold(dold), .dnew(dnew));

   RoundFunction SKINNY (.CLK(clk), .INIT(erst), .ROUND_KEY(TKX), 
			 .ROUND_IN(S), .ROUND_OUT(skinnyS), .CONST_OUT(constant));
   KeyExpansion KEYEXP (.ROUND_KEY(skinnyX), .KEY(TKX));
   
endmodule // mode_top
