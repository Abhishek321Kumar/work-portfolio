<?php

include "process1.php";


?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signup</title>
	<style>
		   <?php include 'css/style.css'; ?>

		   .bg{
  animation:slide 3s ease-in-out infinite alternate;
  background-image: linear-gradient(-60deg, #067c4b  50%, rgb(48, 191, 19) 50%);
  bottom:0;
  left:-50%;
  opacity:.5;
  position:fixed;
  right:-50%;
  top:0;
  z-index:-1;
}

.bg2 {
  animation-direction:alternate-reverse;
  animation-duration:4s;
}

.bg3 {
  animation-duration:5s;
}

.content {
  background-color:rgba(255,255,255,.8);
  border-radius:.25em;
  box-shadow:0 0 .25em rgba(0,0,0,.25);
  box-sizing:border-box;
  left:50%;
  padding:10vmin;
  position:fixed;
  text-align:center;
  top:50%;
  transform:translate(-50%, -50%);
}

h1 {
  font-family:monospace;
}

@keyframes slide {
  0% {
    transform:translateX(-25%);
  }
  100% {
    transform:translateX(25%);
  }
}

		</style>
  
</head>
<body>
<div class="bg"></div>
<div class="bg bg2"></div>
<div class="bg bg3"></div>


<?php

include "signupvalidation.php"
?>
    <section id="navbar">
        <div class="container">
    
         <nav>
           <div class="logo">
               <img src="images/grlogo2.svg" alt="logo">
      
            </div>
          
          <ul>
              <li><a href="http://localhost/major%20project/index.php">Home</a> </li>
              <li><a href="http://localhost/major%20project/aboutus.php">About Us</a> </li>
              <li><a href="http://localhost/major%20project/privacypolicy.php">Privacy Policy</a>  </li>
              <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
              <li> <a id="btn" href="http://localhost/major%20project/login.php"> Login/SignUp</a></li>
              
          </ul>
   
         </nav>        
      
        </div>
   
       </section>

<section id="signup">
    <div class="wrapper">

       
		
		<div class="form_container">
		  <form name="form" method="post">
        <div class="heading">
        <h2>Registration Form</h2>
      </div>
      
            <div class="form_wrap fullname">
				<div class="form_item">
					<label>First Name</label>
					<input type="text" name="ftname" autocomplete="off">
					<div class="error" ><?php echo $fnamerr; ?></div>  
				</div>
				<div class="form_item">
					<label>Last Name</label>
					<input type="text"  name="ltname"  autocomplete="off">
					<div class="error" > <?php echo $lnamerr; ?></div>  
				</div>
			</div>
			<div class="form_wrap">
				<div class="form_item">
					<label>Email Address</label>
					<input type="email" name="email" autocomplete="off">
					<div class="error" id="email"> <?php echo $emailerr; ?></div>  
				</div>
			</div>
			<div class="form_wrap">
				<div class="form_item">
					<label>Phone</label>
					<input type="text"  name="Phonenumber" maxlength="10" autocomplete="off">
					<div class="error" > <?php echo $phnoerr;?> </div>  
				</div>
			</div>

            <div class="form_wrap">
				<div class="form_item">
					<label>Address</label>
					<textarea cols="55" rows="4" maxlength="90" name="address"></textarea>
					<div class="error" > <?php echo $adderr; ?> </div>  
				</div>
			</div>

      

			<div class="form_wrap select_box">
				<div class="form_item">
					<label>State</label>
					<select  name="state" id="state">
                        <option value="Select an option">Select an option</option>
						<option value="Andra Pradesh">Andra Pradesh</option>
						<option value="Karnataka">Karnataka</option>
						<option value="Kerala">Kerala</option>
						<option value="Tamil Nadu">Tamil Nadu</option>
					</select>
					<div class="error" ><?php echo $stateerr; ?></div>  
				</div>
			</div>
            <div class="form_wrap">
				<div class="form_item">
					<label>Create Password</label>
					<input type="password" name="spassword" >
					<div class="error" ><?php echo $spasserr; ?> </div>  
				</div>
			</div>

            <div class="form_wrap">
				<div class="form_item">
					<label>Confirm Password</label>
					<input type="password"  name="conpassword" >
					<div class="error" ><?php echo $cpasserr; ?></div>  
				</div>
			</div>


			<div class="btn">
			  <input type="submit" value="Get Started">
			</div>
		  </form>
		</div>
	  </div>
    </div>
			
    </section>
         
      
    <section id="footer" class="footer">
        <div class="heading2">
         <h2> QuickLinks</h2>
        </div> 
         
         
         <div class="container">
           
            <div class="quicklinks">
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/aboutus.php"> About Us</a></li>
                </ul>
   
                <ul>
           <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
        
                </ul>
   
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/privacypolicy.php"> Privacy Policy</a></li>
                </ul>
   
   
                <ul>
   
                 <li><a href="sale/wanttobuy.php"> Want to Buy?</a></li>
                </ul>
   
   
                </div>
            </div>
   
        
   
     <div class="footlogo">
   
   <img src="images/grlogo2.svg" alt="logo">
     </div>
       </section>

       <script type="text/javascript">

if ( window.history.replaceState ) {
        window.history.replaceState( null, null, window.location.href );
    }

</script>
</body>
</html>
