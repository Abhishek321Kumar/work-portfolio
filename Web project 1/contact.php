
<?php

include "process1.php";
session_start();

$fname=$lname=$mailid=$subject=$description="";
$error="";
$flag=0;


function test_input($data)
{
  $data=trim($data);
  $data=stripslashes($data);
  $data=htmlspecialchars($data);
  return $data;
}


if(isset($_POST["contactsubmit"]))

{

  if(empty($_POST["firstname"])){
    $error.="Please enter the first name "."\\n";
    $flag=1;

  }
  else{
    $fname=test_input($_POST["firstname"]);

    if(!preg_match("/^[a-zA-Z-']*$/",$fname))
    {
      $error.="Enter valid first name"."\\n";
      $flag=1;
    }
  }

  if(empty($_POST["lastname"])){
    $error.="Please enter the Last name"."\\n";
    $flag=1;

  }
  else{
    $lname=test_input($_POST["lastname"]);

    if(!preg_match("/^[a-zA-Z-']*$/",$lname))
    {
      $error.="Enter valid last name"."\\n";
      $flag=1;
    }
  }

  if(empty($_POST["mailid"])){
    $error.="Please enter email"."\\n";
    $flag=1;

  }
  else{

    $mailid=test_input($_POST["mailid"]);
    if(!filter_var($mailid,FILTER_VALIDATE_EMAIL)){
      $error.="Invalid email format"."\\n";
      $flag=1;
    
    }
    
   
  }
  
  if(empty($_POST["subject"])){
    $error.="Please enter the subject "."\\n";
    $flag=1;

  }
  else{


    $subject=test_input($_POST["subject"]);

    if(!preg_match("/[a-zA-Z-' ']/",$subject))
    {
      $error.="Enter valid Subject"."\\n";
      $flag=1;
    }
  }

      $description=test_input($_POST["description"]);

  if($flag==1)
  {
    echo "<script>alert( 'You must follow:\\n'+'$error');</script>";

  }
  else{
    $sql="INSERT INTO `contactpage`(`Name`, `mailid`, `subject`, `description`) VALUES ('$fname $lname','$mailid','$subject','$description')";
    $query=mysqli_query($conn,$sql);

  }


}





?>




<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
<?php include 'css/style.css'; ?>

input[type=text],input[type=email], select, textarea {
  width: 100%;
  padding: 15px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  margin-top: 6px;
  margin-bottom: 16px;
  resize:none;
 
}



input[type=submit] {
  background-color: #04AA6D;
  color: white;
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  position:relative;
  left:50%;
}

input[type=submit]:hover {
  background-color: blue;
}

#contact {
  border-radius: 200px;
  background-color: #00FA9A;
  padding: 50px;
  width:700px;
  margin-left:auto;
  margin-right:auto;
  margin-top:150px;
  margin-bottom:50px;
  box-shadow:80px 0px 0px #52BE80,80px 0px 0px #52BE80;

}

table{
  margin-left:auto;
  margin-right:auto;
  width:80%;
}

h2{ 
text-align:center;
font-size:28px;
margin-bottom:50px;
}

label{
  font-size:18px;
}

.mono{
  color:red;
}



</style>
</head>
<body>
 

  <section id="navbar">
    <div class="container">

     <nav>
       <div class="logo">
           <img src="images/grlogo2.svg" alt="logo">
  
        </div>
      
      <ul id="navmenu">
          <li><a href="http://localhost/major%20project/index.php">Home</a> </li>
          <li><a href="http://localhost/major%20project/aboutus.php">About Us</a> </li>
          <li><a href="http://localhost/major%20project/privacypolicy.php">Privacy Policy</a>  </li>
          <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
        
          
      </ul>

     </nav>        
   
    </div>

   </section>
  



<section id="contact">
  <h2>Contact Form</h2>


    <form method="POST" >
      <table>
        <tr>
  <td> <label for="fname">First Name</label></td> 

   <td> <input type="text" id="fname" name="firstname" placeholder="Your name.." autocomplete="off" ></td>

  </tr>
  <tr class="mono" colspan="2"><td> </td></tr>
  
 <tr>
   <td><label for="lname">Last Name</label> </td> 
   <td> <input type="text" id="lname" name="lastname" placeholder="Your last name.."  autocomplete="off"> </td>
  </tr>
 <tr>
  <td><label for="mail">Mail Id</label></td> 
   <td> <input type="email" id="mail" name="mailid" placeholder="Your Mail Id.."  autocomplete="off"> </td>
  </tr>
 <tr>
<td><label for="subject">Subject</label> </td>
   <td><input type="text" id="subject" name="subject" placeholder="Enter Subject.."  autocomplete="off"> </td> 
  </tr>
    <tr>
    <td><label for="description">Description</label></td>
    <td><textarea id="description" name="description" placeholder="Write something.." style="height:150px"  autocomplete="off"></textarea></td>
  </tr>
</table>
    <input type="submit" value="Submit"  name="contactsubmit">
  
  </form>
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



 <?php   include "user module/activesession.php "; ?>


 <script>
if ( window.history.replaceState ) {
        window.history.replaceState( null, null, window.location.href );
    }

</script>

</body>
</html>
